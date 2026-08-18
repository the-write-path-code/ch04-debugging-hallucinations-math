"""Opik Cloud observability integration with nested spans and metric scores."""

import logging

from opik import Opik

from ch04_eval.config import Settings, get_settings
from ch04_eval.schemas import EvaluationCaseResult

logger = logging.getLogger(__name__)


class OpikTracer:
    """Opik Cloud trace manager for Chapter 4 evaluation pipeline."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.enabled = self.settings.opik_enabled and self.settings.has_opik_key()
        self.client: Opik | None = None

        if self.enabled:
            try:
                self.client = Opik(
                    project_name=self.settings.opik_project_name,
                    workspace=self.settings.opik_workspace or None,
                )
                logger.info(f"Initialized Opik Cloud tracer for project: {self.settings.opik_project_name}")
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Failed to initialize Opik Cloud client: {e}. Tracing disabled.")
                self.enabled = False

    def is_active(self) -> bool:
        """Check if Opik tracing is active."""
        return self.enabled and self.client is not None

    def log_evaluation_case(self, case_result: EvaluationCaseResult) -> str | None:
        """Log a complete evaluation case as an Opik trace with 6 nested spans and scores."""
        if not self.is_active() or self.client is None:
            return None

        try:
            # 1. Create Root Trace for the Evaluation Case
            trace_name = f"evaluation_case_{case_result.case_id}"
            trace_input = {
                "case_id": case_result.case_id,
                "question": case_result.question,
                "risk_tier": case_result.risk_tier.value,
                "expected_answer": case_result.expected_answer,
            }
            trace_output = {
                "decision": case_result.policy_decision.decision.value,
                "decision_reason": case_result.policy_decision.decision_reason,
                "answer": case_result.generation.answer,
                "citations": case_result.generation.citations,
            }
            trace_metadata = {
                "corpus_version": case_result.retrieval.corpus_version,
                "generator_model": case_result.generation.model,
                "judge_model": case_result.grounding.judge_model,
                "threshold_version": case_result.policy_decision.threshold_version,
            }
            tags = [
                f"risk:{case_result.risk_tier.value}",
                f"decision:{case_result.policy_decision.decision.value}",
                f"suff:{case_result.sufficiency.sufficiency_class.value}",
            ]

            trace = self.client.trace(
                name=trace_name,
                input=trace_input,
                output=trace_output,
                metadata=trace_metadata,
                tags=tags,
            )
            trace_id = trace.id

            # 2. Span: Retrieval
            self.client.span(
                trace_id=trace_id,
                name="span_retrieval",
                type="tool",
                input={"query": case_result.retrieval.query},
                output={
                    "retrieved_chunks": [
                        {
                            "chunk_id": c.chunk_id,
                            "rank": c.rank,
                            "score": c.retrieval_score,
                            "doc_id": c.document_id,
                        }
                        for c in case_result.retrieval.retrieved_chunks
                    ]
                },
                metadata={
                    "recall_at_5": case_result.deterministic_metrics.recall_at_k,
                    "precision_at_5": case_result.deterministic_metrics.precision_at_k,
                    "mrr": case_result.deterministic_metrics.mrr,
                },
            )

            # 3. Span: Generation
            self.client.span(
                trace_id=trace_id,
                name="span_generation",
                type="llm",
                input={"question": case_result.question, "chunks": [c.chunk_id for c in case_result.retrieval.retrieved_chunks]},
                output={"answer": case_result.generation.answer, "citations": case_result.generation.citations},
                metadata={"model": case_result.generation.model, "prompt_version": case_result.generation.prompt_version},
            )

            # 4. Span: Ragas Evaluation
            self.client.span(
                trace_id=trace_id,
                name="span_ragas_evaluation",
                type="general",
                input={"answer": case_result.generation.answer},
                output={
                    "context_precision": case_result.ragas_metrics.context_precision,
                    "context_recall": case_result.ragas_metrics.context_recall,
                    "faithfulness": case_result.ragas_metrics.faithfulness,
                    "answer_relevance": case_result.ragas_metrics.answer_relevance,
                },
            )

            # 5. Span: Claim Grounding
            self.client.span(
                trace_id=trace_id,
                name="span_claim_grounding",
                type="llm",
                input={"claims_count": len(case_result.grounding.claims)},
                output={
                    "claim_grounding_rate": case_result.grounding.claim_grounding_rate,
                    "supported": case_result.grounding.supported_claims,
                    "unsupported": case_result.grounding.unsupported_claims,
                    "contradicted": case_result.grounding.contradicted_claims,
                    "claims": [c.model_dump() for c in case_result.grounding.claims],
                },
                metadata={"judge_model": case_result.grounding.judge_model},
            )

            # 6. Span: Sufficiency Evaluation
            self.client.span(
                trace_id=trace_id,
                name="span_sufficiency_evaluation",
                type="llm",
                input={"question": case_result.question},
                output={
                    "sufficiency_class": case_result.sufficiency.sufficiency_class.value,
                    "rationale": case_result.sufficiency.rationale,
                },
                metadata={"judge_model": case_result.sufficiency.judge_model},
            )

            # 7. Span: Policy Decision Gate
            self.client.span(
                trace_id=trace_id,
                name="span_policy_gate",
                type="general",
                input={"metrics_used": case_result.policy_decision.metrics_used},
                output={
                    "decision": case_result.policy_decision.decision.value,
                    "decision_reason": case_result.policy_decision.decision_reason,
                },
                metadata={"threshold_version": case_result.policy_decision.threshold_version},
            )

            # 8. Log Trace Feedback Scores
            feedback_scores = [
                {"name": "recall_at_5", "value": case_result.deterministic_metrics.recall_at_k},
                {"name": "mrr", "value": case_result.deterministic_metrics.mrr},
                {"name": "claim_grounding_rate", "value": case_result.grounding.claim_grounding_rate},
            ]
            if case_result.ragas_metrics.context_precision is not None:
                feedback_scores.append({"name": "context_precision", "value": case_result.ragas_metrics.context_precision})
            if case_result.ragas_metrics.faithfulness is not None:
                feedback_scores.append({"name": "faithfulness", "value": case_result.ragas_metrics.faithfulness})
            if case_result.ragas_metrics.answer_relevance is not None:
                feedback_scores.append({"name": "answer_relevance", "value": case_result.ragas_metrics.answer_relevance})

            try:
                for score in feedback_scores:
                    self.client.log_traces_feedback_scores(
                        scores=[{"id": trace_id, "name": score["name"], "value": float(score["value"])}]
                    )
            except Exception as score_err:  # noqa: BLE001
                logger.warning(f"Could not log trace feedback score: {score_err}")

            return trace_id

        except Exception as e:  # noqa: BLE001
            logger.error(f"Error logging trace to Opik Cloud: {e}")
            return None

    def flush(self) -> None:
        """Flush pending traces to Opik Cloud."""
        if self.is_active() and self.client is not None:
            try:
                self.client.flush()
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Error during Opik flush: {e}")

    def get_project_url(self) -> str | None:
        """Return direct URL to Opik Cloud project dashboard."""
        if self.client is not None:
            try:
                return self.client.get_project_url()
            except Exception as e:  # noqa: BLE001
                logger.debug(f"Could not retrieve project URL: {e}")
        return None
