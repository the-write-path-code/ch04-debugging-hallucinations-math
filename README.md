# Chapter 4: Debugging Hallucinations with Math
Companion repository for Chapter 4 of *The Write Path*.

This project demonstrates how an enterprise RAG system moves from an answer that merely *sounds* plausible to an answer that can be measured, mathematically verified, traced in **Opik Cloud**, and deterministically gated.

---

## Architecture: The 5 Measurement Layers

Rather than collapsing evaluation into a single opaque quality score, the system separates measurement into five distinct layers:

```mermaid
flowchart LR
    Q[Question] --> RET[1. Retrieve Evidence\nBM25 Okapi]
    RET --> GEN[2. Generate Answer\nOllama Cloud + Citations]
    RET --> RM[Layer 1: Deterministic Metrics\nRecall@5, Precision@5, MRR]
    GEN --> RE[Layer 2: Ragas Metrics\nContext Precision, Recall, Faithfulness]
    GEN --> CG[Layer 3: Claim Grounding Judge\nAtomic Claim Verdicts]
    RET --> SUFF[Layer 4: Sufficiency Judge\nSUFFICIENT / INSUFFICIENT]
    RM --> GATE[Layer 5: Deterministic Policy Gate\nZero-LLM Rule Engine]
    RE --> GATE
    CG --> GATE
    SUFF --> GATE
    GATE -->|Pass| ANSWER[ANSWER]
    GATE -->|Partial / Conflict| QUALIFY[QUALIFIED_ANSWER]
    GATE -->|Insufficient| ABSTAIN[ABSTAIN]
    GATE -->|Ungrounded| BLOCK[BLOCK / HUMAN_REVIEW]

    RET -. Trace & Spans .-> OPIK[Opik Cloud Observability]
    GEN -. Trace & Spans .-> OPIK
    RE -. Feedback Scores .-> OPIK
    GATE -. Feedback Scores .-> OPIK
```

---

## Quickstart

### 1. Prerequisites
- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) for package and environment management
- An **Ollama Cloud** API key & **Opik Cloud** API key

### 2. Setup Environment
```bash
git clone https://github.com/mohitagr18/ch04-debugging-hallucinations-math.git
cd ch04-debugging-hallucinations-math
cp .env.example .env
# Edit .env with your OLLAMA_API_KEY and OPIK_API_KEY
uv sync
```

### 3. Run Everything (Single Command)
```bash
# Run the complete end-to-end pipeline in one go
uv run python scripts/run_all.py
```

### 4. Or Run Individual Pipeline Steps
```bash
# 1. Ingest and inspect the policy corpus (23 chunks across 10 documents)
uv run python scripts/ingest_corpus.py

# 2. Run the interactive demo showing all 4 policy gate outcomes
uv run python scripts/run_demo.py

# 3. Execute full multi-layer evaluation and stream traces to Opik Cloud
uv run python scripts/run_evaluation.py

# 4. Evaluate policy threshold calibration matrices
uv run python scripts/calibrate_thresholds.py

# 5. Export evaluation scorecard to CSV (data/artifacts/scorecard.csv)
uv run python scripts/export_scorecard.py

# 6. Run complete test suite (unit tests + live cloud tests)
uv run pytest
```

---

## Evaluation Benchmark & Golden Dataset

The golden evaluation benchmark (`data/golden/golden_dataset_small.csv`) evaluates 12 rigorous enterprise policy cases:

| Case ID | Risk Tier | Scenario / Test Focus | Target Outcome |
|---|---|---|---|
| `case-001` | Low | Core Remote Hours | `ANSWER` |
| `case-002` | Low | 24/7 Ethics Hotline | `ANSWER` |
| `case-003` | Medium | **Stale Policy**: Superseded 2024 vs Active 2026 Per Diem | `ANSWER` (Rejects 2024) |
| `case-004` | Medium | **Conflicting Evidence**: Field Hardware vs General Stipend | `ANSWER` (Exception cited) |
| `case-005` | Medium | **Out-of-Corpus**: Paid Parental Leave Duration | `ABSTAIN` |
| `case-006` | High | **Tempting Hallucination**: Pet Insurance Reimbursement | `ABSTAIN` |
| `case-007` | Low | **Partial Evidence**: International Flight Class Rules | `ABSTAIN` / `QUALIFIED_ANSWER` |
| `case-008` | High | **Compliance Deadline**: Severity 1 60-min Notification | `ANSWER` |
| `case-009` | High | **Data Protection**: 7-Year PII Retention & 48h Erasure | `ANSWER` |
| `case-010` | Medium | **Multi-condition**: Moonlighting Restrictions | `ANSWER` |
| `case-011` | High | **Unsupported Inference**: VP CapEx Signing Limits | `ABSTAIN` / `BLOCK` |
| `case-012` | Medium | **Boundary Limit**: 30-Day Window & 60-Day Forfeiture | `ANSWER` |

---

## Live Opik Cloud Observability

Every execution is logged as an Opik trace with **6 nested spans** and **6 numeric metric dimensions**:
- **Traces**: Input query, golden facts, generator answer, policy decision, and rationale
- **Nested Spans**: `span_retrieval`, `span_generation`, `span_ragas_evaluation`, `span_claim_grounding`, `span_sufficiency_evaluation`, `span_policy_gate`
- **Feedback Scores**: `recall_at_5`, `mrr`, `context_precision`, `faithfulness`, `answer_relevance`, `claim_grounding_rate`

---

## The Chapter 4 Debugging Philosophy: Hallucination Root Cause Triage

When an enterprise RAG system produces an incorrect or misleading statement, the failure almost never stems from a single mysterious "hallucination." Instead, it is the result of a specific breakdown in one of the pipeline stages.

Chapter 4 introduces this systematic triage decision tree to diagnose the exact root cause:

```mermaid
flowchart TD
    X["Observed Output\n(e.g., 'Answer states: 90 days')"] --> C1{"1. Was current policy retrieved?\n[Metric: Recall@5, MRR]"}

    C1 -->|No| R1["Retrieval Failure\n• Fix BM25/vector ranking\n• Fix chunk boundaries\n• Expand corpus coverage"]
    C1 -->|Yes| C2{"2. Did retrieved text state 90 days?\n[Metric: Claim Grounding, Faithfulness]"}

    C2 -->|No| R2["Grounding / Fabrication Failure\n• Fix generation prompt\n• Enforce [doc#chunk] citations\n• Intercept ungrounded claims"]
    C2 -->|Yes| C3{"3. Was source current & sufficient?\n[Metric: Sufficiency Class (Active vs Stale)]"}

    C3 -->|No| R3["Sufficiency / Recency Failure\n• Superseded policy detected (e.g., 2024 vs 2026)\n• Safe Abstention (ABSTAIN) or Escalation"]
    C3 -->|Yes| C4{"4. Did it answer exact claim & jurisdiction?\n[Metric: Answer Relevancy, Context Precision]"}

    C4 -->|No| R4["Scope / Relevance Failure\n• Fix query intent understanding\n• Constrain departmental boundaries"]
    C4 -->|Yes| R5["Grounded & Verified Answer\n• Return ANSWER with verified citations"]
```

---

## Project Structure

```text
ch04-debugging-hallucinations-math/
├── README.md                                 # Overview and execution instructions
├── pyproject.toml                            # Pinned uv project dependencies
├── results.md                                # Single consolidated scorecard report
├── data/
│   ├── source/sample_policy_corpus.md        # 10 policy documents (23 chunks)
│   ├── golden/golden_dataset_small.csv       # 12 golden test cases across risk tiers
│   └── artifacts/                            # Evaluation output dumps (JSONL/CSV)
├── src/ch04_eval/
│   ├── config.py                             # Pydantic settings & validation
│   ├── schemas.py                            # Pydantic models & enums
│   ├── ingest.py                             # Markdown corpus ingestion
│   ├── retrieval.py                          # Okapi BM25 retriever & ranking math
│   ├── generation.py                         # Ollama Cloud generator with citations
│   ├── grounding.py                          # Atomic claim judge & sufficiency judge
│   ├── policy_gate.py                        # Deterministic rule engine & thresholds
│   ├── evaluation.py                         # Ragas metric adapter & orchestrator
│   └── tracing.py                            # Opik Cloud trace & span manager
├── scripts/
│   ├── run_all.py                            # Single-command end-to-end runner
│   ├── ingest_corpus.py                      # Corpus ingestion CLI
│   ├── run_demo.py                           # 4-decision demonstration
│   ├── run_evaluation.py                     # Full evaluation runner & Opik upload
│   ├── calibrate_thresholds.py               # Threshold calibration matrix
│   └── export_scorecard.py                   # Scorecard CSV exporter
├── tests/                                    # 36 automated unit & integration tests
└── workflow/                                 # Mermaid architecture & triage diagrams
    ├── 00_hallucination_root_cause_triage.mmd
    ├── 01_evaluation_layers.mmd
    ├── 02_opik_trace_and_score_flow.mmd
    ├── 03_policy_gate.mmd
    └── 04_threshold_calibration.mmd
```
