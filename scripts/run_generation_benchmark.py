"""Script to run end-to-end retrieval and generation with Ollama Cloud."""

import json
import os

import pandas as pd
from tabulate import tabulate

from ch04_eval.config import get_settings
from ch04_eval.generation import OllamaGenerator
from ch04_eval.ingest import load_corpus
from ch04_eval.retrieval import BM25Retriever


def run_generation_benchmark() -> pd.DataFrame:
    settings = get_settings()
    corpus_chunks = load_corpus(settings.corpus_path)
    retriever = BM25Retriever(corpus_chunks)
    generator = OllamaGenerator(settings=settings)

    df_golden = pd.read_csv(settings.golden_dataset_path)
    os.makedirs(settings.artifacts_dir, exist_ok=True)
    runs_path = os.path.join(settings.artifacts_dir, "generation_runs.jsonl")

    records = []
    jsonl_lines = []

    for _, row in df_golden.iterrows():
        case_id = str(row["id"])
        question = str(row["question"])
        risk_tier = str(row["risk_tier"])
        should_answer = str(row["should_answer"])

        retrieval_res = retriever.retrieve(question, top_k=5)
        gen_res = generator.generate(question, retrieval_res.retrieved_chunks)

        citations_str = ", ".join(gen_res.citations) if gen_res.citations else "(None)"
        # Truncate answer for table display
        short_answer = gen_res.answer[:80] + "..." if len(gen_res.answer) > 80 else gen_res.answer

        records.append(
            {
                "Case ID": case_id,
                "Risk Tier": risk_tier,
                "Should Answer": should_answer,
                "Model": gen_res.model,
                "Citations": citations_str,
                "Generated Answer Preview": short_answer.replace("\n", " "),
            }
        )

        jsonl_lines.append(
            {
                "case_id": case_id,
                "question": question,
                "answer": gen_res.answer,
                "citations": gen_res.citations,
                "model": gen_res.model,
                "prompt_version": gen_res.prompt_version,
                "retrieved_chunk_ids": [c.chunk_id for c in retrieval_res.retrieved_chunks],
            }
        )

    with open(runs_path, "w", encoding="utf-8") as f:
        f.writelines(json.dumps(entry) + "\n" for entry in jsonl_lines)

    return pd.DataFrame(records)


if __name__ == "__main__":
    df = run_generation_benchmark()
    print("=== Phase 4: Generation Benchmark Scorecard ===")
    print(tabulate(df, headers="keys", tablefmt="github", showindex=False))
