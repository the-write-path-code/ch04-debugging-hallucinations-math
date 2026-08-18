# Chapter 4: Debugging hallucinations with math

Companion repository for Chapter 4 of *The Write Path*. The finished project will evaluate retrieval quality, grounding, answer usefulness, and safety decisions for a small RAG pipeline.

## Start here

```bash
git clone https://github.com/mohitagr18/ch04-debugging-hallucinations-math.git
cd ch04-debugging-hallucinations-math
cp .env.example .env
# Add OLLAMA_API_KEY and OPIK_API_KEY to .env
uv sync
uv run pytest
```

The bootstrap environment deliberately has no runtime dependencies yet. The implementation agent must add, verify, lock, and test dependencies incrementally using `uv add`, then commit `pyproject.toml` and `uv.lock`.

## Cloud services

- **Ollama Cloud** will provide generation and the first judge-model path.
- **Opik Cloud** will provide tracing, experiments, datasets, scores, and monitoring.
- No OpenAI, Anthropic, Gemini, Langfuse, or MLflow key is needed for the first version.

## Key files

- [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md): full build plan for the local agent.
- [`docs/UV_BOOTSTRAP.md`](docs/UV_BOOTSTRAP.md): environment and dependency-management instructions.
- [`.env.example`](.env.example): environment variable template.

## Code reuse policy

Code may be reused from repositories owned by `mohitagr18`, subject to compatibility checks and a recorded source path and commit SHA. Do not use code, prompts, datasets, or layouts from `sourangshupal` repositories.
