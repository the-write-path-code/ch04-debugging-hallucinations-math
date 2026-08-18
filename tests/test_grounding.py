"""Unit tests for grounding, atomic claims, and sufficiency judge."""

import pytest

from ch04_eval.config import get_settings
from ch04_eval.grounding import (
    GroundingJudge,
    evaluate_grounding,
    evaluate_sufficiency,
    split_atomic_claims_fallback,
)
from ch04_eval.schemas import (
    ClaimAnalysis,
    ClaimVerdict,
    RetrievedChunk,
    SufficiencyClass,
    SufficiencyResult,
)


def test_split_atomic_claims_fallback():
    """Verify fallback claim splitter cleanly splits sentences and removes citations."""
    text = (
        "Core hours are 10 AM to 3 PM [HR-2026-01#001]. "
        "Employees must be available for meetings Monday through Thursday. "
        "Fridays are reserved for deep work [HR-2026-01#001]."
    )
    claims = split_atomic_claims_fallback(text)
    assert len(claims) == 3
    assert all("[" not in c for c in claims)


def test_grounding_rate_offline_mock():
    """Verify grounding calculation logic with mock verdicts."""
    claims = [
        ClaimAnalysis(claim="C1", verdict=ClaimVerdict.SUPPORTED),
        ClaimAnalysis(claim="C2", verdict=ClaimVerdict.SUPPORTED),
        ClaimAnalysis(claim="C3", verdict=ClaimVerdict.UNSUPPORTED),
        ClaimAnalysis(claim="C4", verdict=ClaimVerdict.NOT_APPLICABLE),
    ]
    res = evaluate_grounding("Q", "A", [], mock_claims=claims)
    # 2 supported out of (2 supported + 1 unsupported) = 2/3 = 0.6667
    assert res.supported_claims == 2
    assert res.unsupported_claims == 1
    assert res.claim_grounding_rate == pytest.approx(0.6667, 0.001)


def test_sufficiency_offline_mock():
    """Verify sufficiency evaluation returns mock result when provided."""
    mock_res = SufficiencyResult(
        sufficiency_class=SufficiencyClass.PARTIAL,
        rationale="Only domestic flight rules are present.",
        judge_model="mock-judge",
    )
    res = evaluate_sufficiency("Q", [], mock_result=mock_res)
    assert res.sufficiency_class == SufficiencyClass.PARTIAL
    assert "domestic" in res.rationale


@pytest.mark.skipif(
    not get_settings().has_ollama_key(),
    reason="OLLAMA_API_KEY not configured; skipping live judge test",
)
def test_live_judge_claim_and_sufficiency():
    """Live judge test against Ollama Cloud."""
    judge = GroundingJudge()
    chunks = [
        RetrievedChunk(
            document_id="SEC-2026-01",
            chunk_id="SEC-2026-01#001",
            text="Customer logs must be retained for 7 years in cold storage.",
            rank=1,
            retrieval_score=1.0,
        )
    ]
    # Test sufficiency
    suff = judge.evaluate_sufficiency(
        "How long are customer logs retained?",
        chunks,
    )
    assert suff.sufficiency_class in {SufficiencyClass.SUFFICIENT, SufficiencyClass.PARTIAL}

    # Test grounding on supported statement
    grounding = judge.evaluate_grounding(
        "How long are customer logs retained?",
        "Customer logs are kept for 7 years in cold storage.",
        chunks,
    )
    assert grounding.claim_grounding_rate >= 0.8
