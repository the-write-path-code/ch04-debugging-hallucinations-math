# Environment bootstrap

## Goal

A user must be able to clone this repository, copy the example environment file, run `uv sync`, and have the intended Python environment ready before any Chapter 4 implementation begins.

## Required local software

- Python 3.11 or newer. This repository requests Python 3.11 through `.python-version`.
- `uv`. Install it using the official Astral instructions for the user’s operating system.
- Git.

## First-run steps

```bash
git clone https://github.com/mohitagr18/ch04-debugging-hallucinations-math.git
cd ch04-debugging-hallucinations-math
cp .env.example .env
uv sync
```

Populate `OLLAMA_API_KEY` and `OPIK_API_KEY` in `.env`. Do not commit that file.

## Agent instructions

1. Start all implementation work from this existing `uv` project.
2. Before adding application code, add verified runtime dependencies with `uv add`.
3. Before adding test, lint, or notebook-only dependencies, add them to the appropriate dependency group with `uv add --group dev` or another intentional group.
4. Run `uv lock` after dependency changes, then commit both `pyproject.toml` and `uv.lock`.
5. Do not hand-edit `uv.lock`.
6. Do not add a package dependency until its current API and Python compatibility have been verified.
7. After each dependency change, run `uv sync` and the relevant smoke test.

## Planned dependencies

Do not add these merely because they appear in the plan. Add them only after verifying compatibility together:

- Ragas, for the Chapter 4 metric adapter.
- Opik, for cloud tracing, experiments, and scores.
- Pydantic and pydantic-settings, for configuration and typed records.
- Pandas, for the small golden dataset and scorecard export.
- An Ollama client or HTTP client compatible with the owner’s Ollama Cloud configuration.
- The selected retrieval and embedding dependencies.

## Verification checklist

The bootstrap phase is complete only when these commands work from a clean checkout:

```bash
uv sync
uv run python --version
uv run pytest
uv run ruff check .
```

At bootstrap, the test suite may contain only a small environment smoke test. Cloud-backed integration tests must remain opt-in and skip when `OLLAMA_API_KEY` or `OPIK_API_KEY` is absent.
