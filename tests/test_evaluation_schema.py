"""Tests for schema models, policy corpus, and golden dataset."""

import os

import pandas as pd

from ch04_eval.schemas import (
    ClaimAnalysis,
    ClaimVerdict,
    GoldenTestCase,
    GroundingResult,
    PolicyDecision,
    PolicyDecisionResult,
    RiskTier,
)


def test_sample_policy_corpus_exists():
    """Verify that sample policy corpus is present and populated."""
    corpus_path = "data/source/sample_policy_corpus.md"
    assert os.path.exists(corpus_path), f"Corpus not found at {corpus_path}"
    with open(corpus_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert len(content) > 1000
    assert "SEC-2026-01" in content
    assert "SEC-2026-02" in content
    assert "SEC-2026-03" in content
    assert "HR-2026-01" in content
    assert "HR-2026-02" in content
    assert "HR-2026-03" in content
    assert "FIN-2024-03" in content
    assert "FIN-2026-03" in content
    assert "FIN-2026-04" in content
    assert "OPS-2026-04" in content
    assert "SUPERSEDED" in content
    assert "CONFLICTING" in content


def test_golden_dataset_structure_and_coverage():
    """Verify golden dataset CSV loads correctly with expected distribution."""
    dataset_path = "data/golden/golden_dataset_small.csv"
    assert os.path.exists(dataset_path), f"Dataset not found at {dataset_path}"

    df = pd.read_csv(dataset_path)
    assert len(df) >= 10, "Golden dataset must contain at least 10 cases"

    expected_cols = [
        "id",
        "question",
        "expected_answer",
        "expected_facts",
        "relevant_document_ids",
        "risk_tier",
        "should_answer",
        "notes",
    ]
    for col in expected_cols:
        assert col in df.columns, f"Missing column: {col}"

    # Verify risk tiers cover low, medium, and high
    risk_tiers = set(df["risk_tier"].dropna().str.lower())
    assert {"low", "medium", "high"}.issubset(risk_tiers)

    # Verify out-of-corpus / should_answer == 'False' exists
    abstain_cases = df[df["should_answer"].astype(str).str.lower() == "false"]
    assert len(abstain_cases) >= 2, "Must contain cases requiring abstention"

    # Verify partial case exists
    partial_cases = df[df["should_answer"].astype(str).str.lower() == "partial"]
    assert len(partial_cases) >= 1, "Must contain partial-evidence case"


def test_golden_test_case_pydantic_parsing():
    """Verify GoldenTestCase parses rows correctly."""
    df = pd.read_csv("data/golden/golden_dataset_small.csv")
    for _, row in df.iterrows():
        doc_ids = []
        if pd.notna(row["relevant_document_ids"]):
            doc_ids = [d.strip() for d in str(row["relevant_document_ids"]).split(";") if d.strip()]
        case = GoldenTestCase(
            id=str(row["id"]),
            question=str(row["question"]),
            expected_answer=str(row["expected_answer"]),
            expected_facts=str(row["expected_facts"]),
            relevant_document_ids=doc_ids,
            risk_tier=RiskTier(str(row["risk_tier"]).lower()),
            should_answer=str(row["should_answer"]),
            notes=str(row["notes"]) if pd.notna(row["notes"]) else "",
        )
        assert case.id.startswith("case-")
        assert len(case.question) > 5


def test_grounding_rate_computation():
    """Verify grounding result model validation and claim rate arithmetic."""
    claim1 = ClaimAnalysis(
        claim="The allowance is $90 per day.",
        verdict=ClaimVerdict.SUPPORTED,
        evidence_chunk_ids=["FIN-2026-03#001"],
        rationale="Explicitly stated in section 1.",
    )
    claim2 = ClaimAnalysis(
        claim="Receipts are optional.",
        verdict=ClaimVerdict.CONTRADICTED,
        evidence_chunk_ids=["FIN-2026-03#001"],
        rationale="Section 1 states itemized receipts are mandatory.",
    )
    res = GroundingResult(
        claims=[claim1, claim2],
        supported_claims=1,
        unsupported_claims=0,
        contradicted_claims=1,
        claim_grounding_rate=0.5,
        judge_model="llama3.2",
    )
    assert res.claim_grounding_rate == 0.5
    assert len(res.claims) == 2


def test_policy_decision_result():
    """Verify policy decision model serializes and retains rationale."""
    p = PolicyDecisionResult(
        decision=PolicyDecision.QUALIFIED_ANSWER,
        decision_reason="Evidence is partial for international travel.",
        metrics_used={"claim_grounding_rate": 1.0, "sufficiency": "PARTIAL"},
        threshold_version="v1.0",
    )
    assert p.decision == PolicyDecision.QUALIFIED_ANSWER
    assert p.decision_reason.startswith("Evidence is partial")
