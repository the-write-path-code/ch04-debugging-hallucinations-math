"""Unit tests for Opik Cloud tracing, spans, and feedback score logging."""

import pytest

from ch04_eval.config import Settings, get_settings
from ch04_eval.schemas import (
    ClaimAnalysis,
    ClaimVerdict,
    DeterministicMetrics,
    EvaluationCaseResult,
    GenerationResult,
    GroundingResult,
    PolicyDecision,
    PolicyDecisionResult,
    RagasMetrics,
    RetrievalResult,
    RetrievedChunk,
    RiskTier,
    SufficiencyClass,
    SufficiencyResult,
)
from ch04_eval.tracing import OpikTracer


def make_dummy_case_result() -> EvaluationCaseResult:
    """Helper to construct a fully populated EvaluationCaseResult."""
    retrieval = RetrievalResult(
        query="What are the core hours?",
        retrieved_chunks=[
            RetrievedChunk(
                document_id="HR-2026-01",
                chunk_id="HR-2026-01#001",
                text="Core hours are 10 AM to 3 PM.",
                rank=1,
                retrieval_score=0.95,
            )
        ],
    )
    det_metrics = DeterministicMetrics(recall_at_k=1.0, precision_at_k=0.2, mrr=1.0)
    generation = GenerationResult(
        answer="Core hours are 10 AM to 3 PM [HR-2026-01#001].",
        citations=["HR-2026-01#001"],
        model="gpt-oss:20b",
    )
    ragas_metrics = RagasMetrics(
        context_precision=0.85,
        context_recall=1.0,
        faithfulness=1.0,
        answer_relevance=0.9,
    )
    grounding = GroundingResult(
        claims=[
            ClaimAnalysis(
                claim="Core hours are 10 AM to 3 PM",
                verdict=ClaimVerdict.SUPPORTED,
                evidence_chunk_ids=["HR-2026-01#001"],
            )
        ],
        supported_claims=1,
        unsupported_claims=0,
        claim_grounding_rate=1.0,
        judge_model="gpt-oss:20b",
    )
    sufficiency = SufficiencyResult(
        sufficiency_class=SufficiencyClass.SUFFICIENT,
        rationale="Sufficient evidence.",
        judge_model="gpt-oss:20b",
    )
    policy_decision = PolicyDecisionResult(
        decision=PolicyDecision.ANSWER,
        decision_reason="All thresholds satisfied.",
        metrics_used={"claim_grounding_rate": 1.0},
    )

    return EvaluationCaseResult(
        case_id="case-trace-test-01",
        question="What are the core hours?",
        risk_tier=RiskTier.LOW,
        expected_answer="10 AM to 3 PM",
        retrieval=retrieval,
        deterministic_metrics=det_metrics,
        generation=generation,
        ragas_metrics=ragas_metrics,
        grounding=grounding,
        sufficiency=sufficiency,
        policy_decision=policy_decision,
    )


def test_opik_tracer_disabled_mode():
    """Verify tracer does not error and returns None when disabled or key missing."""
    settings = Settings(opik_api_key=None, opik_enabled=False, _env_file=None)
    tracer = OpikTracer(settings=settings)
    assert not tracer.is_active()

    case_result = make_dummy_case_result()
    trace_id = tracer.log_evaluation_case(case_result)
    assert trace_id is None


@pytest.mark.skipif(
    not get_settings().has_opik_key(),
    reason="OPIK_API_KEY not configured; skipping live Opik Cloud integration test",
)
def test_live_opik_cloud_tracing():
    """Verify live trace with nested spans and feedback scores logs to Opik Cloud."""
    tracer = OpikTracer()
    assert tracer.is_active()

    case_result = make_dummy_case_result()
    trace_id = tracer.log_evaluation_case(case_result)
    tracer.flush()

    assert trace_id is not None
    assert len(trace_id) > 5
