"""Core evaluation pipeline integrating Ragas metrics, grounding checks, and judge signals."""

import logging

from ch04_eval.config import Settings, get_settings
from ch04_eval.generation import OllamaGenerator
from ch04_eval.grounding import GroundingJudge
from ch04_eval.retrieval import BM25Retriever, compute_deterministic_metrics
from ch04_eval.schemas import (
    EvaluationCaseResult,
    GoldenTestCase,
    GroundingResult,
    PolicyDecision,
    PolicyDecisionResult,
    RagasMetrics,
    RetrievedChunk,
    SufficiencyResult,
)

logger = logging.getLogger(__name__)


def compute_heuristic_ragas_metrics(
    question: str,
    answer: str,
    retrieved_chunks: list[RetrievedChunk],
    expected_answer: str,
    grounding_result: GroundingResult,
    sufficiency_result: SufficiencyResult,
) -> RagasMetrics:
    """Compute normalized Ragas-aligned metric scores from evidence, grounding, and recall.

    This ensures reproducible, transparent score calculation aligned with Chapter 4 math:
    - context_precision: rank-weighted placement of relevant chunks in top-K
    - context_recall: proportion of required factual concepts found in context
    - faithfulness: claim grounding rate (supported claims / all evaluable claims)
    - answer_relevance: semantic alignment between question intent and answer content
    """
    # 1. Faithfulness is directly the claim grounding rate
    faithfulness = float(grounding_result.claim_grounding_rate)

    # 2. Context Precision: Higher when top-ranked chunks have higher retrieval scores and relevance
    if not retrieved_chunks:
        context_precision = 0.0
    else:
        # Precision weighted by reciprocal rank of chunks with positive relevance
        precision_sum = 0.0
        for i, c in enumerate(retrieved_chunks, start=1):
            weight = 1.0 / i
            # Check if chunk text contains keywords from question or answer
            q_words = set(question.lower().split())
            overlap = sum(1 for w in q_words if len(w) > 3 and w in c.text.lower())
            chunk_relevance = min(1.0, overlap / max(1, len(q_words) // 2))
            precision_sum += weight * chunk_relevance
        context_precision = min(1.0, round(precision_sum / sum(1.0 / i for i in range(1, len(retrieved_chunks) + 1)), 4))

    # 3. Context Recall: Based on sufficiency class
    if sufficiency_result.sufficiency_class.value == "SUFFICIENT":
        context_recall = 1.0
    elif sufficiency_result.sufficiency_class.value in {"PARTIAL", "CONFLICTING"}:
        context_recall = 0.65
    else:
        context_recall = 0.0

    # 4. Answer Relevance: Check question intent coverage and abstention consistency
    if "does not contain information" in answer.lower():
        # If answering out-of-corpus query, abstention is 100% relevant
        answer_relevance = 1.0 if sufficiency_result.sufficiency_class.value == "INSUFFICIENT" else 0.5
    else:
        # Check answer length and question term presence
        q_terms = [w for w in question.lower().split() if len(w) > 3]
        matched = sum(1 for w in q_terms if w in answer.lower())
        answer_relevance = min(1.0, round(0.5 + 0.5 * (matched / max(1, len(q_terms))), 4))

    return RagasMetrics(
        context_precision=context_precision,
        context_recall=context_recall,
        faithfulness=faithfulness,
        answer_relevance=answer_relevance,
    )


class RAGEvaluator:
    """End-to-end evaluation orchestrator for Chapter 4."""

    def __init__(
        self,
        retriever: BM25Retriever,
        generator: OllamaGenerator | None = None,
        judge: GroundingJudge | None = None,
        settings: Settings | None = None,
    ):
        self.settings = settings or get_settings()
        self.retriever = retriever
        self.generator = generator or OllamaGenerator(settings=self.settings)
        self.judge = judge or GroundingJudge(settings=self.settings)

    def evaluate_case(
        self,
        test_case: GoldenTestCase,
        top_k: int = 5,
        mock_answer: str | None = None,
        mock_claims: list | None = None,
        mock_sufficiency: SufficiencyResult | None = None,
    ) -> EvaluationCaseResult:
        """Run full 5-layer evaluation on a single golden test case."""
        # Layer 1: Retrieval & Deterministic Metrics
        retrieval_res = self.retriever.retrieve(test_case.question, top_k=top_k)
        deterministic_metrics = compute_deterministic_metrics(
            retrieval_res,
            test_case.relevant_document_ids,
            k=top_k,
        )

        # Layer 2: Grounded Generation
        generation_res = self.generator.generate(
            test_case.question,
            retrieval_res.retrieved_chunks,
            mock_response=mock_answer,
        )

        # Layer 3: Claim Grounding Judge
        grounding_res = self.judge.evaluate_grounding(
            test_case.question,
            generation_res.answer,
            retrieval_res.retrieved_chunks,
            mock_claims=mock_claims,
        )

        # Layer 4: Evidence Sufficiency Judge
        sufficiency_res = self.judge.evaluate_sufficiency(
            test_case.question,
            retrieval_res.retrieved_chunks,
            mock_result=mock_sufficiency,
        )

        # Layer 3/4: Ragas Metric Aggregation
        ragas_metrics = compute_heuristic_ragas_metrics(
            question=test_case.question,
            answer=generation_res.answer,
            retrieved_chunks=retrieval_res.retrieved_chunks,
            expected_answer=test_case.expected_answer,
            grounding_result=grounding_res,
            sufficiency_result=sufficiency_res,
        )

        # Layer 5: Policy Gate Decision (Standard rules)
        # Evaluated deterministically
        if sufficiency_res.sufficiency_class.value in {"INSUFFICIENT"}:
            decision = PolicyDecision.ABSTAIN
            reason = "Retrieved evidence is insufficient for the question."
        elif sufficiency_res.sufficiency_class.value == "CONFLICTING":
            decision = PolicyDecision.QUALIFIED_ANSWER if test_case.risk_tier.value != "high" else PolicyDecision.HUMAN_REVIEW
            reason = "Conflicting policy clauses detected across departments."
        elif grounding_res.claim_grounding_rate < 0.80 or grounding_res.unsupported_claims > 0:
            if test_case.risk_tier.value == "high":
                decision = PolicyDecision.BLOCK
                reason = "High-risk question contained unsupported claims."
            else:
                decision = PolicyDecision.HUMAN_REVIEW
                reason = "Generated answer contains ungrounded claims."
        elif sufficiency_res.sufficiency_class.value == "PARTIAL":
            decision = PolicyDecision.QUALIFIED_ANSWER
            reason = "Evidence is partial; answer qualified with scope constraints."
        elif test_case.risk_tier.value == "high" and (ragas_metrics.faithfulness or 1.0) < 0.95:
            decision = PolicyDecision.HUMAN_REVIEW
            reason = "High-risk question fell below faithfulness threshold."
        else:
            decision = PolicyDecision.ANSWER
            reason = "Retrieved evidence sufficient and answer fully grounded."

        policy_decision = PolicyDecisionResult(
            decision=decision,
            decision_reason=reason,
            metrics_used={
                "recall_at_5": deterministic_metrics.recall_at_k,
                "context_precision": ragas_metrics.context_precision,
                "faithfulness": ragas_metrics.faithfulness,
                "claim_grounding_rate": grounding_res.claim_grounding_rate,
                "sufficiency": sufficiency_res.sufficiency_class.value,
                "risk_tier": test_case.risk_tier.value,
            },
            threshold_version="v1.0",
            corpus_version=retrieval_res.corpus_version,
            evaluation_run_id=test_case.id,
        )

        return EvaluationCaseResult(
            case_id=test_case.id,
            question=test_case.question,
            risk_tier=test_case.risk_tier,
            expected_answer=test_case.expected_answer,
            retrieval=retrieval_res,
            deterministic_metrics=deterministic_metrics,
            generation=generation_res,
            ragas_metrics=ragas_metrics,
            grounding=grounding_res,
            sufficiency=sufficiency_res,
            policy_decision=policy_decision,
        )
