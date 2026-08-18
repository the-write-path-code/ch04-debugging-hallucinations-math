"""Single unified runner script executing the complete Chapter 4 evaluation pipeline."""

from rich.console import Console
from rich.panel import Panel

from ch04_eval.config import get_settings
from scripts.calibrate_thresholds import evaluate_threshold_profile, load_evaluation_artifacts
from scripts.export_scorecard import export_scorecard
from scripts.ingest_corpus import main as ingest_corpus_main
from scripts.run_demo import run_demo
from scripts.run_evaluation import run_evaluation_pipeline

console = Console()


def run_all() -> None:
    settings = get_settings()
    console.print(Panel.fit(
        "[bold cyan]Chapter 4: Complete End-to-End Evaluation Pipeline[/bold cyan]\n"
        "[dim]Ingestion -> Demo -> Evaluation & Opik Upload -> Calibration -> Scorecard Export[/dim]",
        border_style="cyan",
    ))

    # Step 1: Ingest Corpus
    console.print("\n[bold yellow]Step 1/5: Ingesting Policy Corpus...[/bold yellow]")
    ingest_corpus_main()

    # Step 2: Run Interactive Demo
    console.print("\n[bold yellow]Step 2/5: Running Decision Gate Demo (4 Core Scenarios)...[/bold yellow]")
    run_demo()

    # Step 3: Run Full Evaluation Pipeline & Stream Traces to Opik
    console.print("\n[bold yellow]Step 3/5: Executing Multi-Layer Evaluation & Opik Cloud Trace Logging...[/bold yellow]")
    df_eval = run_evaluation_pipeline()
    console.print(f"Evaluated {len(df_eval)} test cases across all 5 measurement layers.")

    # Step 4: Calibrate Policy Gate Thresholds
    console.print("\n[bold yellow]Step 4/5: Running Threshold Calibration Analysis...[/bold yellow]")
    records = load_evaluation_artifacts(settings)
    from ch04_eval.policy_gate import PolicyThresholds
    std_profile = PolicyThresholds(version="v1.0-standard")
    evaluate_threshold_profile(records, std_profile)
    console.print(f"[green]Threshold Analysis Complete:[/green] Evaluated {len(records)} records across low, medium, and high risk tiers.")

    # Step 5: Export Final Scorecard CSV
    console.print("\n[bold yellow]Step 5/5: Exporting Scorecard Artifacts...[/bold yellow]")
    export_scorecard()

    console.print(Panel.fit(
        f"[bold green]✔ All Pipeline Steps Successfully Completed![/bold green]\n\n"
        f"• Local Scorecard CSV: [bold]{settings.artifacts_dir}/scorecard.csv[/bold]\n"
        f"• Evaluation JSONL: [bold]{settings.artifacts_dir}/evaluation_results.jsonl[/bold]\n"
        f"• Consolidated Report: [bold]results.md[/bold]",
        border_style="green",
    ))


if __name__ == "__main__":
    run_all()
