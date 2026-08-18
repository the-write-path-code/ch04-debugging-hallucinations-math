"""Unit tests for deterministic PolicyGate rules, decisions, and edge-case behaviors."""

from ch04_eval.policy_gate import evaluate_policy_gate
from ch04_eval.schemas import (
    ClaimAnalysis,
    ClaimVerdict,
    DeterministicMetrics,
    GroundingResult,
    PolicyDecision,
    RagasMetrics,
    RiskTier,
    SufficiencyClass,
    SufficiencyResult,
)


def make_dummy_inputs(
    risk_tier: RiskTier = RiskTier.LOW,
    sufficiency: SufficiencyClass = SufficiencyClass.SUFFICIENT,
    grounding_rate: float = 1.0,
    unsupported_claims: int = 0,
    faithfulness: float = 1.0,
):
    """Helper to create dummy inputs for policy gate testing."""
    det_metrics = DeterministicMetrics(recall_at_k=1.0, precision_at_k=0.2, mrr=1.0)
    ragas_metrics = RagasMetrics(
        context_precision=0.8,
        context_recall=1.0,
        faithfulness=faithfulness,
        answer_relevance=0.9,
    )
    claims = []
    if unsupported_claims > 0:
        claims.append(ClaimAnalysis(claim="Fake claim", verdict=ClaimVerdict.UNSUPPORTED))
    grounding_res = GroundingResult(
        claims=claims,
        supported_claims=1 if grounding_rate > 0 else 0,
        unsupported_claims=unsupported_claims,
        claim_grounding_rate=grounding_rate,
    )
    suff_res = SufficiencyResult(
        sufficiency_class=sufficiency,
        rationale="Test rationale",
    )
    return risk_tier, det_metrics, ragas_metrics, grounding_res, suff_res


def test_insufficient_evidence_triggers_abstain():
    """Verify Rule 1: Insufficient evidence always triggers ABSTAIN regardless of risk tier."""
    for tier in [RiskTier.LOW, RiskTier.MEDIUM, RiskTier.HIGH]:
        args = make_dummy_inputs(risk_tier=tier, sufficiency=SufficiencyClass.INSUFFICIENT)
        res = evaluate_policy_gate(*args)
        assert res.decision == PolicyDecision.ABSTAIN
        assert "insufficient" in res.decision_reason.lower()


def test_conflicting_evidence_branching():
    """Verify Rule 2: Conflicting evidence escalates to HUMAN_REVIEW for high-risk, QUALIFIED for others."""
    # High risk -> HUMAN_REVIEW
    args_high = make_dummy_inputs(risk_tier=RiskTier.HIGH, sufficiency=SufficiencyClass.CONFLICTING)
    res_high = evaluate_policy_gate(*args_high)
    assert res_high.decision == PolicyDecision.HUMAN_REVIEW

    # Low risk -> QUALIFIED_ANSWER
    args_low = make_dummy_inputs(risk_tier=RiskTier.LOW, sufficiency=SufficiencyClass.CONFLICTING)
    res_low = evaluate_policy_gate(*args_low)
    assert res_low.decision == PolicyDecision.QUALIFIED_ANSWER


def test_unsupported_claim_triggers_block():
    """Verify Rule 4: Fabricated unsupported claims trigger BLOCK."""
    args = make_dummy_inputs(
        risk_tier=RiskTier.LOW,
        sufficiency=SufficiencyClass.SUFFICIENT,
        grounding_rate=0.5,
        unsupported_claims=1,
    )
    res = evaluate_policy_gate(*args)
    assert res.decision == PolicyDecision.BLOCK
    assert "unsupported" in res.decision_reason.lower() or "violated" in res.decision_reason.lower()


def test_high_risk_faithfulness_below_threshold_triggers_review():
    """Verify Rule 3: High-risk question with faithfulness below 0.95 triggers HUMAN_REVIEW."""
    args = make_dummy_inputs(
        risk_tier=RiskTier.HIGH,
        sufficiency=SufficiencyClass.SUFFICIENT,
        grounding_rate=0.96,  # below 0.98
        faithfulness=0.92,  # below 0.95
    )
    res = evaluate_policy_gate(*args)
    assert res.decision == PolicyDecision.HUMAN_REVIEW


def test_partial_evidence_triggers_qualified_answer():
    """Verify Rule 5: Partial evidence on grounded answer produces QUALIFIED_ANSWER."""
    args = make_dummy_inputs(risk_tier=RiskTier.LOW, sufficiency=SufficiencyClass.PARTIAL)
    res = evaluate_policy_gate(*args)
    assert res.decision == PolicyDecision.QUALIFIED_ANSWER
    assert "partial" in res.decision_reason.lower()


def test_sufficient_and_grounded_triggers_answer():
    """Verify Rule 6: Fully grounded answer with sufficient evidence produces ANSWER."""
    args = make_dummy_inputs(risk_tier=RiskTier.LOW, sufficiency=SufficiencyClass.SUFFICIENT)
    res = evaluate_policy_gate(*args)
    assert res.decision == PolicyDecision.ANSWER
