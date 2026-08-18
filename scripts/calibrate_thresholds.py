"""Threshold calibration script evaluating safety profiles across risk tiers."""

import json
import os
import sys

import pandas as pd
from tabulate import tabulate

from ch04_eval.config import get_settings
from ch04_eval.policy_gate import PolicyGate, PolicyThresholds
from ch04_eval.schemas import (
    DeterministicMetrics,
    GroundingResult,
    RagasMetrics,
    RiskTier,
    SufficiencyClass,
    SufficiencyResult,
)


def load_evaluation_artifacts(settings) -> list[dict]:
    """Load existing evaluation_results.jsonl artifact."""
    results_path = os.path.join(settings.artifacts_dir, "evaluation_results.jsonl")
    if not os.path.exists(results_path):
        print(f"Error: Evaluation artifact not found at {results_path}", file=sys.stderr)
        print("Please run `uv run python scripts/run_evaluation.py` first.", file=sys.stderr)
        sys.exit(1)

    records = []
    with open(results_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line.strip()))
    return records


def evaluate_threshold_profile(records: list[dict], thresholds: PolicyThresholds) -> dict:
    """Evaluate a specific threshold profile against all evaluation records."""
    gate = PolicyGate(thresholds=thresholds)
    df_golden = pd.read_csv(get_settings().golden_dataset_path).set_index("id")

    tier_stats = {
        "low": {
            "ANSWER": 0,
            "QUALIFIED_ANSWER": 0,
            "ABSTAIN": 0,
            "BLOCK": 0,
            "HUMAN_REVIEW": 0,
            "false_pass": 0,
            "false_block": 0,
        },
        "medium": {
            "ANSWER": 0,
            "QUALIFIED_ANSWER": 0,
            "ABSTAIN": 0,
            "BLOCK": 0,
            "HUMAN_REVIEW": 0,
            "false_pass": 0,
            "false_block": 0,
        },
        "high": {
            "ANSWER": 0,
            "QUALIFIED_ANSWER": 0,
            "ABSTAIN": 0,
            "BLOCK": 0,
            "HUMAN_REVIEW": 0,
            "false_pass": 0,
            "false_block": 0,
        },
    }

    for rec in records:
        case_id = rec["case_id"]
        risk = rec["risk_tier"]
        golden_row = df_golden.loc[case_id] if case_id in df_golden.index else None
        should_answer = (
            str(golden_row["should_answer"]).lower() if golden_row is not None else "true"
        )

        det_metrics = DeterministicMetrics(**rec["deterministic_metrics"])
        ragas_metrics = RagasMetrics(**rec["ragas_metrics"])
        grounding_res = GroundingResult(**rec["grounding"])
        sufficiency_res = SufficiencyResult(**rec["sufficiency"])

        decision_res = gate.evaluate(
            risk_tier=RiskTier(risk),
            deterministic_metrics=det_metrics,
            ragas_metrics=ragas_metrics,
            grounding_result=grounding_res,
            sufficiency_result=sufficiency_res,
            corpus_version=rec.get("retrieval", {}).get("corpus_version", "2026.1"),
            evaluation_run_id=case_id,
        )

        dec = decision_res.decision.value
        tier_stats[risk][dec] += 1

        # Check safety violations
        if should_answer == "false" and dec in {"ANSWER", "QUALIFIED_ANSWER"}:
            tier_stats[risk]["false_pass"] += 1
        elif (
            should_answer == "true"
            and sufficiency_res.sufficiency_class == SufficiencyClass.SUFFICIENT
            and dec in {"BLOCK", "ABSTAIN"}
        ):
            tier_stats[risk]["false_block"] += 1

    return tier_stats


def main() -> None:
    settings = get_settings()
    records = load_evaluation_artifacts(settings)

    profiles = [
        PolicyThresholds(
            version="v1.0-standard",
            claim_grounding_min=0.95,
            high_risk_grounding_min=0.98,
            faithfulness_min=0.90,
            high_risk_faithfulness_min=0.95,
        ),
        PolicyThresholds(
            version="v1.1-strict-safety",
            claim_grounding_min=0.98,
            high_risk_grounding_min=1.00,
            faithfulness_min=0.95,
            high_risk_faithfulness_min=0.99,
        ),
        PolicyThresholds(
            version="v1.2-exploratory",
            claim_grounding_min=0.80,
            high_risk_grounding_min=0.90,
            faithfulness_min=0.80,
            high_risk_faithfulness_min=0.85,
        ),
    ]

    print("=================================================================")
    print("        Chapter 4: Policy Gate Threshold Calibration Matrix       ")
    print("=================================================================\n")

    summary_rows = []

    for prof in profiles:
        stats = evaluate_threshold_profile(records, prof)
        for risk, counts in stats.items():
            summary_rows.append(
                {
                    "Profile": prof.version,
                    "Risk Tier": risk.upper(),
                    "Answer": counts["ANSWER"],
                    "Qualify": counts["QUALIFIED_ANSWER"],
                    "Abstain": counts["ABSTAIN"],
                    "Block": counts["BLOCK"],
                    "Review": counts["HUMAN_REVIEW"],
                    "False Pass": counts["false_pass"],
                    "False Block": counts["false_block"],
                }
            )

    df_summary = pd.DataFrame(summary_rows)
    print(tabulate(df_summary, headers="keys", tablefmt="github", showindex=False))

    print("\n[NOTE] Calibration Status: PROVISIONAL.")
    print("These threshold matrices are calibrated against the golden baseline.")
    print(
        "In accordance with Chapter 4 requirements, no threshold profile is declared production-frozen until human review audit labels are integrated."
    )


if __name__ == "__main__":
    main()
