"""Deterministic policy gating engine and threshold configuration."""

from dataclasses import dataclass
from typing import Any

from ch04_eval.schemas import (
    DeterministicMetrics,
    GroundingResult,
    PolicyDecision,
    PolicyDecisionResult,
    RagasMetrics,
    RiskTier,
    SufficiencyClass,
    SufficiencyResult,
)


@dataclass
class PolicyThresholds:
    """Configurable threshold profile for deterministic policy gating."""

    version: str = "v1.0"
    recall_at_5_min: float = 0.90
    context_precision_min: float = 0.75
    faithfulness_min: float = 0.90
    answer_relevance_min: float = 0.80
    claim_grounding_min: float = 0.95
    high_risk_faithfulness_min: float = 0.95
    high_risk_grounding_min: float = 0.98


class PolicyGate:
    """Deterministic, rule-driven policy gate."""

    def __init__(self, thresholds: PolicyThresholds | None = None):
        self.thresholds = thresholds or PolicyThresholds()

    def evaluate(
        self,
        risk_tier: RiskTier,
        deterministic_metrics: DeterministicMetrics,
        ragas_metrics: RagasMetrics,
        grounding_result: GroundingResult,
        sufficiency_result: SufficiencyResult,
        corpus_version: str = "2026.1",
        evaluation_run_id: str = "",
    ) -> PolicyDecisionResult:
        """Evaluate signals deterministically and return policy decision with detailed rationale."""
        sufficiency_val = sufficiency_result.sufficiency_class
        grounding_rate = grounding_result.claim_grounding_rate
        faithfulness = ragas_metrics.faithfulness if ragas_metrics.faithfulness is not None else 1.0
        risk = risk_tier.value

        metrics_used: dict[str, Any] = {
            "risk_tier": risk,
            "sufficiency_class": sufficiency_val.value,
            "claim_grounding_rate": grounding_rate,
            "faithfulness": faithfulness,
            "context_precision": ragas_metrics.context_precision,
            "recall_at_5": deterministic_metrics.recall_at_k,
            "unsupported_claims": grounding_result.unsupported_claims,
            "contradicted_claims": grounding_result.contradicted_claims,
        }

        # Rule 1: Insufficient evidence forces immediate abstention
        if sufficiency_val == SufficiencyClass.INSUFFICIENT:
            decision = PolicyDecision.ABSTAIN
            reason = "Retrieved evidence is insufficient to answer the question safely."

        # Rule 2: Conflicting evidence handling
        elif sufficiency_val == SufficiencyClass.CONFLICTING:
            if risk == "high":
                decision = PolicyDecision.HUMAN_REVIEW
                reason = "Conflicting policy rules detected in high-risk scenario; escalating to human review."
            else:
                decision = PolicyDecision.QUALIFIED_ANSWER
                reason = "Conflicting departmental rules detected; answer qualified with explicit exceptions."

        # Rule 3: High-risk tier strict thresholds
        elif risk == "high" and grounding_rate < self.thresholds.high_risk_grounding_min:
            decision = PolicyDecision.HUMAN_REVIEW
            reason = (
                f"High-risk question claim grounding ({grounding_rate:.2f}) fell below "
                f"strict safety threshold ({self.thresholds.high_risk_grounding_min:.2f})."
            )
        elif risk == "high" and faithfulness < self.thresholds.high_risk_faithfulness_min:
            decision = PolicyDecision.HUMAN_REVIEW
            reason = (
                f"High-risk question faithfulness ({faithfulness:.2f}) fell below "
                f"strict threshold ({self.thresholds.high_risk_faithfulness_min:.2f})."
            )

        # Rule 4: General ungrounded claims trigger Block
        elif (
            grounding_rate < self.thresholds.claim_grounding_min
            or grounding_result.unsupported_claims > 0
        ):
            if risk == "high":
                decision = PolicyDecision.BLOCK
                reason = "High-risk answer contained unsupported factual claims."
            else:
                decision = PolicyDecision.BLOCK
                reason = (
                    f"Claim grounding rate ({grounding_rate:.2f}) violated minimum "
                    f"standard ({self.thresholds.claim_grounding_min:.2f})."
                )

        # Rule 5: Partial evidence produces qualified answers
        elif sufficiency_val == SufficiencyClass.PARTIAL:
            decision = PolicyDecision.QUALIFIED_ANSWER
            reason = "Evidence is partial; answer qualified with explicit scope limits."

        # Rule 6: All checks passed
        else:
            decision = PolicyDecision.ANSWER
            reason = "All evidence sufficiency and grounding safety thresholds satisfied."

        return PolicyDecisionResult(
            decision=decision,
            decision_reason=reason,
            metrics_used=metrics_used,
            threshold_version=self.thresholds.version,
            corpus_version=corpus_version,
            evaluation_run_id=evaluation_run_id,
        )


def evaluate_policy_gate(
    risk_tier: RiskTier,
    deterministic_metrics: DeterministicMetrics,
    ragas_metrics: RagasMetrics,
    grounding_result: GroundingResult,
    sufficiency_result: SufficiencyResult,
    thresholds: PolicyThresholds | None = None,
    corpus_version: str = "2026.1",
    evaluation_run_id: str = "",
) -> PolicyDecisionResult:
    """Convenience function for policy evaluation."""
    gate = PolicyGate(thresholds=thresholds)
    return gate.evaluate(
        risk_tier=risk_tier,
        deterministic_metrics=deterministic_metrics,
        ragas_metrics=ragas_metrics,
        grounding_result=grounding_result,
        sufficiency_result=sufficiency_result,
        corpus_version=corpus_version,
        evaluation_run_id=evaluation_run_id,
    )
