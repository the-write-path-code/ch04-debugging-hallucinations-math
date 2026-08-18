"""Script to run retrieval benchmark on the golden dataset and export artifacts."""

import json
import os

import pandas as pd
from tabulate import tabulate

from ch04_eval.config import get_settings
from ch04_eval.ingest import load_corpus
from ch04_eval.retrieval import BM25Retriever, compute_deterministic_metrics


def run_retrieval_benchmark() -> pd.DataFrame:
    settings = get_settings()
    corpus_chunks = load_corpus(settings.corpus_path)
    retriever = BM25Retriever(corpus_chunks)

    df_golden = pd.read_csv(settings.golden_dataset_path)
    os.makedirs(settings.artifacts_dir, exist_ok=True)
    runs_path = os.path.join(settings.artifacts_dir, "retrieval_runs.jsonl")

    records = []
    jsonl_lines = []

    for _, row in df_golden.iterrows():
        case_id = str(row["id"])
        question = str(row["question"])
        risk_tier = str(row["risk_tier"])
        should_answer = str(row["should_answer"])

        rel_doc_ids = []
        if pd.notna(row["relevant_document_ids"]):
            rel_doc_ids = [
                d.strip() for d in str(row["relevant_document_ids"]).split(";") if d.strip()
            ]

        retrieval_res = retriever.retrieve(question, top_k=5)
        metrics = compute_deterministic_metrics(retrieval_res, rel_doc_ids, k=5)
        top_chunk_id = (
            retrieval_res.retrieved_chunks[0].chunk_id if retrieval_res.retrieved_chunks else "N/A"
        )

        records.append(
            {
                "Case ID": case_id,
                "Risk Tier": risk_tier,
                "Should Answer": should_answer,
                "Relevant Docs": "; ".join(rel_doc_ids) if rel_doc_ids else "(Out of corpus)",
                "Top Retrieved": top_chunk_id,
                "Recall@5": metrics.recall_at_k,
                "Precision@5": metrics.precision_at_k,
                "MRR": metrics.mrr,
            }
        )

        jsonl_lines.append(
            {
                "case_id": case_id,
                "question": question,
                "relevant_document_ids": rel_doc_ids,
                "retrieved_chunks": [c.model_dump() for c in retrieval_res.retrieved_chunks],
                "metrics": metrics.model_dump(),
            }
        )

    with open(runs_path, "w", encoding="utf-8") as f:
        f.writelines(json.dumps(entry) + "\n" for entry in jsonl_lines)

    return pd.DataFrame(records)


if __name__ == "__main__":
    df = run_retrieval_benchmark()
    print("=== Phase 3: Retrieval Benchmark Scorecard ===")
    print(tabulate(df, headers="keys", tablefmt="github", showindex=False))
