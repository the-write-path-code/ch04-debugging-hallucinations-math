# Chapter 4: Debugging Hallucinations with Math

Companion code for *Building Safe Agentic AI for Enterprise Systems* by Mohit Aggarwal.

This repository evaluates a policy-compliance RAG system through a fixed five-layer stack. It separates retrieval failure, unsupported claims, insufficient or conflicting evidence, and scope errors before a deterministic policy gate chooses one outcome: `ANSWER`, `QUALIFIED_ANSWER`, `ABSTAIN`, `BLOCK`, or `HUMAN_REVIEW`.

The main lesson is that “the RAG system hallucinated” is not a diagnosis. A wrong answer can begin with the wrong retrieval result, a claim that the evidence does not support, a superseded document, insufficient evidence, or a response to the wrong policy scope. Each failure needs a different correction.

## What You Will Run

| Chapter section | Demonstration | What it shows |
| --- | --- | --- |
| 4.1 | Root-cause triage | A fixed sequence for locating a wrong answer in retrieval, claim grounding, evidence sufficiency, or scope interpretation. |
| 4.2 | Five-layer evaluation stack | Retrieval metrics, Ragas-aligned metrics, claim-level grounding, sufficiency classification, and a deterministic policy gate. |
| 4.3 | Tracing | Structured evaluation traces and spans, with optional export to Opik Cloud. |
| 4.4 | Grounding thresholds | A rule cascade that routes each case to an answer, qualified answer, abstention, block, or human review. |
| 4.5 | Threshold calibration | A matrix that compares threshold profiles against saved evaluation results and counts false passes and false blocks by risk tier. |

The repository uses a synthetic policy corpus and a labeled golden dataset. It is designed to make evaluation behavior inspectable and repeatable without exposing company policy documents.

## Production Warning

The scores in this repository are evidence for a policy decision, not a policy decision by themselves. A score with decimals does not become trustworthy because it has a decimal point. The deterministic policy gate, its rule order, the risk tier, and the evidence record determine what the system does.

The Ragas metric names in the repository follow standard evaluation vocabulary, but the companion implementation uses its own explicit formulas. In particular, its `faithfulness` value equals the claim grounding rate. Do not treat those two fields as independent confirmation of the same answer.

## Prerequisites

- Git
- [uv](https://docs.astral.sh/uv/)
- Python 3.11
- A configured Ollama service or Ollama Cloud endpoint for full generation and evaluation runs
- An Ollama API key when your selected endpoint requires one

Opik Cloud is optional. The repository runs without Opik tracing when the Opik credentials and enablement setting are absent.

## Quick Start

### 1. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone and synchronize the repository

```bash
git clone https://github.com/the-write-path-code/ch04-debugging-hallucinations-math.git
cd ch04-debugging-hallucinations-math
uv sync
```

The repository includes `uv.lock` and `.python-version`. Run `uv sync` after pulling changes so your local environment matches the committed dependency set.

### 3. Create local configuration

```bash
cp .env.example .env
```

Set the Ollama values that match your environment. For Ollama Cloud, supply the endpoint, API key, generator model, and judge model. For a local service, use the appropriate local endpoint and installed model names.

```dotenv
OLLAMA_BASE_URL=https://api.ollama.com
OLLAMA_API_KEY=your-key
OLLAMA_MODEL=your-generator-model
OLLAMA_JUDGE_MODEL=your-judge-model
```

Do not commit `.env`.

## Configuration

The root `.env.example` is the only file you need to edit for local credentials and external service configuration.

### Ollama generation and judging

| Variable | Purpose |
| --- | --- |
| `OLLAMA_BASE_URL` | Ollama Cloud endpoint or local Ollama URL |
| `OLLAMA_API_KEY` | Required when the selected endpoint requires authentication |
| `OLLAMA_MODEL` | Model used to generate answers from retrieved policy chunks |
| `OLLAMA_JUDGE_MODEL` | Model used when the claim or sufficiency judge is configured to use a model |

### Opik tracing, optional

| Variable | Purpose |
| --- | --- |
| `OPIK_ENABLED` | Enables or disables export of traces to Opik |
| `OPIK_API_KEY` | Opik credential, required only when tracing is enabled |
| `OPIK_PROJECT_NAME` | Target Opik project; defaults to the Chapter 4 project name |
| `OPIK_WORKSPACE` | Optional workspace selection |
| `OPIK_URL_OVERRIDE` | Optional custom Opik endpoint |

When Opik tracing is disabled or credentials are absent, the evaluation pipeline still runs. It does not attempt to write remote traces.

> **Tip**
>
> Run the four-case demo before the full evaluation. It lets you inspect each possible routing outcome before you process the full golden dataset.

## Run the Chapter Demonstrations

### 1. Inspect Corpus Ingestion, Section 4.1

```bash
uv run python scripts/ingest_corpus.py
```

The command reads the synthetic policy corpus, splits it into chunks, and prints document and chunk counts. This is the first place to look if a retrieval result is wrong because the expected source cannot be retrieved if it never entered the corpus correctly.

### 2. Run the Four-Outcome Demo, Sections 4.1 through 4.4

```bash
uv run python scripts/run_demo.py
```

The demo selects representative golden cases and shows how the five evaluation layers lead to different policy decisions:

- A standard answerable question routes to `ANSWER`.
- A question with a scope exception or conflicting evidence can route to `QUALIFIED_ANSWER`.
- An out-of-corpus question routes to `ABSTAIN`.
- An unsupported inference routes to `BLOCK` or `HUMAN_REVIEW`, depending on the rule cascade and risk tier.

For each case, inspect the retrieved chunks, generated answer, metrics, claim verdicts, sufficiency decision, and final policy-gate decision. A final answer alone is not enough to explain why the gate chose it.

### 3. Run the Full Evaluation, Sections 4.2 and 4.3

```bash
uv run python scripts/run_evaluation.py
```

The runner evaluates every case in the golden dataset and writes its artifacts under the configured artifacts directory. The output includes the per-case retrieval results, generated answer, citations, Ragas-aligned scores, claim-level verdicts, sufficiency classification, and policy-gate decision.

When Opik is enabled, the evaluator writes one root trace per case with child spans for retrieval, generation, metric evaluation, claim grounding, sufficiency, and policy gating.

### 4. Calibrate Threshold Profiles, Section 4.5

Run calibration after the full evaluation has produced its artifact file:

```bash
uv run python scripts/calibrate_thresholds.py
```

The calibration script applies threshold profiles to saved evaluation records and prints a decision matrix by risk tier. It counts two error types:

- A false pass: a case that should not answer receives `ANSWER` or `QUALIFIED_ANSWER`.
- A false block: a case that should answer receives `ABSTAIN` or `BLOCK`.

Threshold profiles remain provisional until human-review audit evidence exists. Do not freeze a threshold profile solely because it produces attractive aggregate scores.

### 5. Run the Full Sequence

```bash
uv run python scripts/run_all.py
```

The unified runner performs corpus ingestion, the four-case demo, full evaluation, threshold calibration, and scorecard export in that order.

## Expected Results

The golden dataset contains 12 synthetic enterprise-policy cases across low, medium, and high risk tiers. It includes answerable questions, stale-policy scenarios, conflicting policies, out-of-corpus questions, partial evidence, and unsupported inference attempts.

The important output is the decision trail for each case. A case that reaches `ANSWER` should have retrieved the expected source, supported claims, sufficient evidence, and a passing rule-gate path. A case that does not meet those conditions should be abstained, blocked, qualified, or escalated according to the rule order.

The five evaluation layers are:

1. **Retrieval metrics:** Recall@5, Precision@5, and mean reciprocal rank (MRR) measure whether the expected policy document was retrieved and how highly it ranked.
2. **Ragas-aligned metrics:** Context precision, context recall, faithfulness, and answer relevance summarize retrieval and answer alignment using the repository's explicit formulas.
3. **Claim grounding:** Each factual claim is classified as `SUPPORTED`, `UNSUPPORTED`, `CONTRADICTED`, or `NOT_APPLICABLE`.
4. **Sufficiency evaluation:** Retrieved evidence is classified as `SUFFICIENT`, `PARTIAL`, `INSUFFICIENT`, or `CONFLICTING` without looking at the generated answer.
5. **Policy gate:** A deterministic rule cascade combines the typed results and risk tier into one action.

The policy gate is ordered. A perfect claim-grounding rate does not rescue insufficient evidence, and a fully sufficient retrieval result does not rescue an unsupported claim.

## Run the Tests

```bash
uv run pytest
```

The repository’s tests cover retrieval metrics, claim-grounding verdicts, sufficiency classification, policy-gate rule ordering, threshold calibration, trace construction, and the full evaluation path.

Run the full suite before changing a threshold, a golden case, an evaluation formula, or a prompt. A passing test suite does not prove a policy is correct, but it does establish that the implementation still follows its declared contract.

## Repository Layout

```text
.
├── README.md
├── pyproject.toml
├── uv.lock
├── .python-version
├── .env.example
├── data/
│   ├── source/                      # Synthetic policy corpus
│   └── golden/                      # Labeled 12-case evaluation dataset
├── artifacts/                       # Generated evaluation records and scorecards
├── src/ch04_eval/
│   ├── config.py                    # Pydantic settings and paths
│   ├── schemas.py                   # Typed evaluation models and enums
│   ├── ingest.py                    # Corpus ingestion and chunking
│   ├── retrieval.py                 # BM25 retrieval and deterministic metrics
│   ├── generation.py                # Ollama-backed generation and citations
│   ├── evaluation.py                # Ragas-aligned metric adapter
│   ├── grounding.py                 # Claim grounding and evidence sufficiency
│   ├── policy_gate.py               # Deterministic decision cascade
│   ├── tracing.py                   # Optional Opik tracing
│   └── orchestrator.py              # Five-layer evaluation assembly
├── scripts/
│   ├── ingest_corpus.py
│   ├── run_demo.py
│   ├── run_evaluation.py
│   ├── calibrate_thresholds.py
│   ├── export_scorecard.py
│   └── run_all.py
├── tests/
└── workflow/
    ├── 00_hallucination_root_cause_triage.mmd
    └── ...                           # Five-layer, tracing, gate, and calibration diagrams
```

## Architecture Diagrams and Supporting Documents

The `workflow/` directory contains the diagrams used in Chapter 4, including:

- The root-cause triage for a single wrong answer.
- The five-layer evaluation stack.
- The trace-and-score structure for one case.
- The deterministic policy-gate rule cascade.
- The threshold-calibration workflow.

The source modules map directly to these diagrams. Start with `workflow/00_hallucination_root_cause_triage.mmd` when a case produces an unexpected answer or action.

## Safety and Operational Limits

- The corpus and golden cases are synthetic teaching artifacts, not a corporate policy system.
- Citation extraction confirms that a citation token is present. It does not establish that the nearby claim is supported. The claim-grounding layer performs that check.
- In this implementation, faithfulness equals claim grounding rate. Do not count them as two independent signals.
- The sufficiency judge evaluates only the question and retrieved chunks. It cannot repair a poor generated answer, and the generator cannot make insufficient evidence sufficient.
- Opik tracing records what the pipeline did. It does not score cases or approve a decision.
- Thresholds must be calibrated against labeled cases and reviewed for false-pass and false-block behavior. They are not universal constants.

## Troubleshooting

### `uv sync` fails

Confirm that uv is current and that Python 3.11 is available:

```bash
uv --version
uv python list
```

### The generator cannot connect to Ollama

Check `OLLAMA_BASE_URL`, your API key if required, and the configured model names in `.env`. For local Ollama, confirm that the service is running and the model is installed.

### Opik tracing is not visible

Tracing is optional. Confirm that `OPIK_ENABLED` is true and that the Opik credentials, workspace, project name, and endpoint settings are correct. Evaluation artifacts should still be written locally when tracing is disabled.

### Threshold calibration cannot find evaluation results

Run the full evaluation first:

```bash
uv run python scripts/run_evaluation.py
```

Calibration reads the saved evaluation artifact. It does not rerun generation.

### A case is blocked when you expected an answer

Use the root-cause triage in the workflow directory. Check retrieval before changing the policy gate, claim grounding before changing the generator prompt, and evidence sufficiency before changing a threshold. Do not start by lowering the threshold.

## Related Chapters

- Chapter 3 measures retrieval design before generation and policy evaluation.
- Chapter 5 adds corrective routing and recursive retrieval when evidence is incomplete or weak.
- Chapter 14 applies the same fail-closed reasoning to security controls and action boundaries.
- Chapter 15 turns evaluation baselines, threshold profiles, and policy outcomes into CI merge gates.

## License and Errata

See `LICENSE` for licensing terms. Report documentation or code issues through this repository's GitHub issue tracker.
