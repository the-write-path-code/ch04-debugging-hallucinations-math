"""Script to run full multi-layer evaluation across the golden dataset."""

import json
import os

import pandas as pd
from tabulate import tabulate

from ch04_eval.config import get_settings
from ch04_eval.evaluation import RAGEvaluator
from ch04_eval.ingest import load_corpus
from ch04_eval.retrieval import BM25Retriever
from ch04_eval.schemas import GoldenTestCase, RiskTier


def run_evaluation_pipeline() -> pd.DataFrame:
    settings = get_settings()
    corpus_chunks = load_corpus(settings.corpus_path)
    retriever = BM25Retriever(corpus_chunks)
    evaluator = RAGEvaluator(retriever=retriever, settings=settings)

    df_golden = pd.read_csv(settings.golden_dataset_path)
    os.makedirs(settings.artifacts_dir, exist_ok=True)
    results_path = os.path.join(settings.artifacts_dir, "evaluation_results.jsonl")

    records = []
    jsonl_lines = []

    for _, row in df_golden.iterrows():
        rel_docs = []
        if pd.notna(row["relevant_document_ids"]):
            rel_docs = [
                d.strip() for d in str(row["relevant_document_ids"]).split(";") if d.strip()
            ]

        test_case = GoldenTestCase(
            id=str(row["id"]),
            question=str(row["question"]),
            expected_answer=str(row["expected_answer"]),
            expected_facts=str(row["expected_facts"]),
            relevant_document_ids=rel_docs,
            risk_tier=RiskTier(str(row["risk_tier"]).lower()),
            should_answer=str(row["should_answer"]),
            notes=str(row["notes"]) if pd.notna(row["notes"]) else "",
        )

        res = evaluator.evaluate_case(test_case=test_case, top_k=5)

        records.append(
            {
                "Case ID": res.case_id,
                "Risk": res.risk_tier.value,
                "Recall@5": res.deterministic_metrics.recall_at_k,
                "Ctx Precision": res.ragas_metrics.context_precision,
                "Faithfulness": res.ragas_metrics.faithfulness,
                "Relevance": res.ragas_metrics.answer_relevance,
                "Grounding": res.grounding.claim_grounding_rate,
                "Sufficiency": res.sufficiency.sufficiency_class.value,
                "Policy Decision": res.policy_decision.decision.value,
            }
        )

        jsonl_lines.append(res.model_dump())

    with open(results_path, "w", encoding="utf-8") as f:
        f.writelines(json.dumps(entry) + "\n" for entry in jsonl_lines)

    return pd.DataFrame(records)


if __name__ == "__main__":
    df = run_evaluation_pipeline()
    print("=== Phase 5: Multi-Layer Evaluation Scorecard ===")
    print(tabulate(df, headers="keys", tablefmt="github", showindex=False))
