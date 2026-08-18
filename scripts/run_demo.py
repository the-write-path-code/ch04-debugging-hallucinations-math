"""Interactive and automated Chapter 4 demo demonstrating all policy gate outcomes."""

import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ch04_eval.config import get_settings
from ch04_eval.evaluation import RAGEvaluator
from ch04_eval.ingest import load_corpus
from ch04_eval.retrieval import BM25Retriever
from ch04_eval.schemas import GoldenTestCase, RiskTier

console = Console()


def run_demo() -> None:
    settings = get_settings()
    console.print(
        Panel.fit(
            "[bold cyan]Chapter 4: Debugging Hallucinations with Math[/bold cyan]\n"
            "[dim]Demonstrating 5-Layer RAG Evaluation, Claim-Level Grounding & Policy Gating[/dim]",
            border_style="cyan",
        )
    )

    corpus_chunks = load_corpus(settings.corpus_path)
    retriever = BM25Retriever(corpus_chunks)
    evaluator = RAGEvaluator(retriever=retriever, settings=settings)

    df_golden = pd.read_csv(settings.golden_dataset_path).set_index("id")

    # Select representative cases for each distinct policy outcome
    demo_cases = [
        ("case-001", "ANSWER", "Standard Low-Risk Answerable Case"),
        ("case-004", "QUALIFIED_ANSWER", "Departmental Conflicting Rule Exception"),
        ("case-005", "ABSTAIN", "Out-of-Corpus Query Requiring Abstention"),
        ("case-011", "BLOCK / ABSTAIN", "High-Risk Unsupported Inference & Gating"),
    ]

    for case_id, expected_decision, description in demo_cases:
        if case_id not in df_golden.index:
            continue

        row = df_golden.loc[case_id]
        rel_docs = (
            [d.strip() for d in str(row["relevant_document_ids"]).split(";") if d.strip()]
            if pd.notna(row["relevant_document_ids"])
            else []
        )

        test_case = GoldenTestCase(
            id=case_id,
            question=str(row["question"]),
            expected_answer=str(row["expected_answer"]),
            expected_facts=str(row["expected_facts"]),
            relevant_document_ids=rel_docs,
            risk_tier=RiskTier(str(row["risk_tier"]).lower()),
            should_answer=str(row["should_answer"]),
            notes=str(row["notes"]) if pd.notna(row["notes"]) else "",
        )

        console.print(f"\n[bold yellow]━━━ Case: {case_id} ({description}) ━━━[/bold yellow]")
        console.print(f"[bold]Question:[/bold] {test_case.question}")
        console.print(f"[bold]Risk Tier:[/bold] [{test_case.risk_tier.value.upper()}]")

        result = evaluator.evaluate_case(test_case=test_case, top_k=5)

        # Display Metrics & Decision Table
        table = Table(
            title=f"Evaluation Trace for {case_id}", show_header=True, header_style="bold magenta"
        )
        table.add_column("Layer / Signal", style="cyan")
        table.add_column("Measurement / Value", style="white")

        table.add_row(
            "1. Retrieval Recall@5",
            f"{result.deterministic_metrics.recall_at_k:.2f} (MRR: {result.deterministic_metrics.mrr:.2f})",
        )
        table.add_row(
            "2. Top Chunk Retrived",
            result.retrieval.retrieved_chunks[0].chunk_id
            if result.retrieval.retrieved_chunks
            else "None",
        )
        table.add_row(
            "3. Generated Citations",
            ", ".join(result.generation.citations) if result.generation.citations else "(None)",
        )
        table.add_row(
            "4. Context Precision", f"{result.ragas_metrics.context_precision or 0.0:.3f}"
        )
        table.add_row("5. Faithfulness", f"{result.ragas_metrics.faithfulness or 0.0:.3f}")
        table.add_row(
            "6. Claim Grounding Rate",
            f"{result.grounding.claim_grounding_rate:.2f} ({result.grounding.supported_claims} supp, {result.grounding.unsupported_claims} unsupp)",
        )
        table.add_row(
            "7. Evidence Sufficiency",
            f"[{result.sufficiency.sufficiency_class.value}] {result.sufficiency.rationale}",
        )

        color_map = {
            "ANSWER": "green",
            "QUALIFIED_ANSWER": "yellow",
            "ABSTAIN": "blue",
            "BLOCK": "red",
            "HUMAN_REVIEW": "magenta",
        }
        dec_color = color_map.get(result.policy_decision.decision.value, "white")
        table.add_row(
            "8. Policy Gate Decision",
            f"[{dec_color} bold]{result.policy_decision.decision.value}[/{dec_color} bold]",
        )
        table.add_row("   Decision Reason", f"{result.policy_decision.decision_reason}")

        console.print(table)
        console.print(f"[bold dim]Generated Answer:[/bold dim] {result.generation.answer}\n")

    project_url = evaluator.tracer.get_project_url()
    if project_url:
        console.print(
            Panel(
                f"[bold green]Live Opik Dashboard:[/bold green] [link={project_url}]{project_url}[/link]",
                border_style="green",
            )
        )


if __name__ == "__main__":
    run_demo()
