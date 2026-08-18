"""Export scorecard CSV from evaluation artifacts."""

import json
import os
import sys

import pandas as pd
from tabulate import tabulate

from ch04_eval.config import get_settings


def export_scorecard() -> pd.DataFrame:
    settings = get_settings()
    results_path = os.path.join(settings.artifacts_dir, "evaluation_results.jsonl")
    scorecard_csv_path = os.path.join(settings.artifacts_dir, "scorecard.csv")

    if not os.path.exists(results_path):
        print(f"Error: Evaluation artifact not found at {results_path}", file=sys.stderr)
        print("Please run `uv run python scripts/run_evaluation.py` first.", file=sys.stderr)
        sys.exit(1)

    records = []
    with open(results_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data = json.loads(line.strip())
                records.append(
                    {
                        "case_id": data["case_id"],
                        "question": data["question"],
                        "risk_tier": data["risk_tier"],
                        "recall_at_5": data["deterministic_metrics"]["recall_at_k"],
                        "mrr": data["deterministic_metrics"]["mrr"],
                        "context_precision": data["ragas_metrics"]["context_precision"],
                        "context_recall": data["ragas_metrics"]["context_recall"],
                        "faithfulness": data["ragas_metrics"]["faithfulness"],
                        "answer_relevance": data["ragas_metrics"]["answer_relevance"],
                        "claim_grounding_rate": data["grounding"]["claim_grounding_rate"],
                        "supported_claims": data["grounding"]["supported_claims"],
                        "unsupported_claims": data["grounding"]["unsupported_claims"],
                        "sufficiency_class": data["sufficiency"]["sufficiency_class"],
                        "policy_decision": data["policy_decision"]["decision"],
                        "decision_reason": data["policy_decision"]["decision_reason"],
                    }
                )

    df = pd.DataFrame(records)
    df.to_csv(scorecard_csv_path, index=False)
    print(f"Scorecard successfully exported to: {scorecard_csv_path}\n")
    return df


def main() -> None:
    df = export_scorecard()
    display_cols = [
        "case_id",
        "risk_tier",
        "recall_at_5",
        "context_precision",
        "faithfulness",
        "claim_grounding_rate",
        "sufficiency_class",
        "policy_decision",
    ]
    print(tabulate(df[display_cols], headers="keys", tablefmt="github", showindex=False))


if __name__ == "__main__":
    main()
