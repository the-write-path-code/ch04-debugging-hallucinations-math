"""Unit tests for RAGEvaluator and Ragas metrics adapter."""

from ch04_eval.evaluation import RAGEvaluator, compute_heuristic_ragas_metrics
from ch04_eval.ingest import load_corpus
from ch04_eval.retrieval import BM25Retriever
from ch04_eval.schemas import (
    ClaimAnalysis,
    ClaimVerdict,
    GoldenTestCase,
    GroundingResult,
    PolicyDecision,
    RetrievedChunk,
    RiskTier,
    SufficiencyClass,
    SufficiencyResult,
)


def test_compute_heuristic_ragas_metrics_bounds():
    """Verify Ragas metric calculation produces valid bounded floats in [0, 1]."""
    chunks = [
        RetrievedChunk(
            document_id="SEC-2026-01",
            chunk_id="SEC-2026-01#001",
            text="Customer logs must be retained for 7 years.",
            rank=1,
            retrieval_score=1.0,
        )
    ]
    grounding = GroundingResult(
        claims=[ClaimAnalysis(claim="Retained 7 years", verdict=ClaimVerdict.SUPPORTED)],
        supported_claims=1,
        unsupported_claims=0,
        claim_grounding_rate=1.0,
    )
    sufficiency = SufficiencyResult(
        sufficiency_class=SufficiencyClass.SUFFICIENT,
        rationale="All info present",
    )

    metrics = compute_heuristic_ragas_metrics(
        question="How long are logs kept?",
        answer="Logs are kept for 7 years.",
        retrieved_chunks=chunks,
        expected_answer="7 years",
        grounding_result=grounding,
        sufficiency_result=sufficiency,
    )

    assert 0.0 <= metrics.context_precision <= 1.0
    assert 0.0 <= metrics.context_recall <= 1.0
    assert metrics.faithfulness == 1.0
    assert 0.0 <= metrics.answer_relevance <= 1.0


def test_rag_evaluator_end_to_end_mock():
    """Verify RAGEvaluator runs all 5 evaluation layers offline with mock fixtures."""
    corpus = load_corpus("data/source/sample_policy_corpus.md")
    retriever = BM25Retriever(corpus)
    evaluator = RAGEvaluator(retriever=retriever)

    test_case = GoldenTestCase(
        id="case-test-01",
        question="What are the core collaboration hours?",
        expected_answer="10 AM to 3 PM",
        expected_facts="10:00 AM to 3:00 PM Eastern",
        relevant_document_ids=["HR-2026-01"],
        risk_tier=RiskTier.LOW,
        should_answer="True",
    )

    mock_answer = "Core hours are 10 AM to 3 PM [HR-2026-01#001]."
    mock_claims = [
        ClaimAnalysis(
            claim="Core hours are 10 AM to 3 PM",
            verdict=ClaimVerdict.SUPPORTED,
            evidence_chunk_ids=["HR-2026-01#001"],
        )
    ]
    mock_sufficiency = SufficiencyResult(
        sufficiency_class=SufficiencyClass.SUFFICIENT,
        rationale="Sufficient",
    )

    result = evaluator.evaluate_case(
        test_case=test_case,
        mock_answer=mock_answer,
        mock_claims=mock_claims,
        mock_sufficiency=mock_sufficiency,
    )

    assert result.case_id == "case-test-01"
    assert result.deterministic_metrics.recall_at_k == 1.0
    assert result.generation.citations == ["HR-2026-01#001"]
    assert result.grounding.claim_grounding_rate == 1.0
    assert result.sufficiency.sufficiency_class == SufficiencyClass.SUFFICIENT
    assert result.policy_decision.decision == PolicyDecision.ANSWER
