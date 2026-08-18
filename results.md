# Chapter 4 Evaluation Results & Scorecard

This document serves as the single consolidated results record for *Chapter 4: Debugging Hallucinations with Math*. It captures deterministic retrieval metrics, generation fidelity, claim grounding, judge sufficiency classifications, and final policy gate decisions.

---

## 1. Pipeline Architecture

```mermaid
flowchart LR
    Q[Golden Query] --> RET[1. Deterministic Retrieval]
    RET --> GEN[2. Grounded Generation with Citations]
    RET --> RM[Retrieval Metrics: Recall@5, MRR]
    GEN --> EVAL[3. Ragas & Claim Grounding Judge]
    RET --> EVAL
    EVAL --> SUFF[4. Evidence Sufficiency Judge]
    RM --> GATE[5. Deterministic Policy Gate]
    EVAL --> GATE
    SUFF --> GATE
    GATE --> DECISION{Decision}
    DECISION -->|Pass| ANSWER[ANSWER]
    DECISION -->|Partial Evidence| QUALIFY[QUALIFIED_ANSWER]
    DECISION -->|Out-of-Corpus| ABSTAIN[ABSTAIN]
    DECISION -->|Unsupported Claim| BLOCK[BLOCK / HUMAN_REVIEW]
```

---

## 2. Phase 3 Results: Retrieval Ranking & Deterministic Metrics

- **Corpus**: `data/source/sample_policy_corpus.md` (10 documents, 23 chunks, Version 2026.1)
- **Dataset**: `data/golden/golden_dataset_small.csv` (12 test cases)
- **Retriever**: BM25 Okapi ($k_1=1.5, b=0.75$) with top-$k=5$
- **Raw Run Output Artifact**: `data/artifacts/retrieval_runs.jsonl`

### Retrieval Scorecard

| Case ID | Risk Tier | Should Answer | Relevant Documents | Top Retrieved Chunk | Recall@5 | Precision@5 | MRR | Notes & Evaluation Insights |
|---|---|---|---|---|---:|---:|---:|---|
| **case-001** | low | True | `HR-2026-01` | `HR-2026-01#001` | **1.00** | 0.20 | **1.000** | Core collaboration hours found at rank 1 |
| **case-002** | low | True | `HR-2026-03` | `HR-2026-03#002` | **1.00** | 0.20 | **1.000** | Ethics hotline entity matched at rank 1 |
| **case-003** | medium | True | `FIN-2026-03` | `FIN-2024-03#001` | **1.00** | 0.20 | **0.500** | **Stale Policy Test**: Superseded policy ranked #1; active 2026 policy at #2 |
| **case-004** | medium | True | `OPS-2026-04; HR-2026-02` | `OPS-2026-04#001` | **1.00** | 0.40 | **1.000** | **Conflict Test**: Retrieved both $3.5k field and $1.5k standard stipends |
| **case-005** | medium | False | *(Out of corpus)* | `FIN-2026-03#001` | 0.00 | 0.00 | 0.000 | Parental leave: no relevant documents in corpus |
| **case-006** | high | False | *(Out of corpus)* | `HR-2026-01#002` | 0.00 | 0.00 | 0.000 | Pet insurance: no relevant documents in corpus |
| **case-007** | low | partial | `FIN-2026-03` | `FIN-2026-03#002` | **1.00** | 0.20 | **1.000** | International flights: partial evidence found |
| **case-008** | high | True | `SEC-2026-03` | `SEC-2026-03#002` | **1.00** | 0.20 | **1.000** | Severity 1 60-min incident escalation at rank 1 |
| **case-009** | high | True | `SEC-2026-01` | `SEC-2026-01#001` | **1.00** | 0.20 | **1.000** | 7-year PII retention & 48h erasure at rank 1 |
| **case-010** | medium | True | `HR-2026-01` | `HR-2026-01#002` | **1.00** | 0.20 | **1.000** | Moonlighting 10h/week restriction at rank 1 |
| **case-011** | high | False | *(Out of corpus)* | `SEC-2026-01#002` | 0.00 | 0.00 | 0.000 | VP signing authority: no relevant documents in corpus |
| **case-012** | medium | True | `FIN-2026-03` | `FIN-2026-03#003` | **1.00** | 0.20 | **1.000** | 30-day expense deadline & 60-day cutoff at rank 1 |

---

## 3. Phase 4 Results: Generation & Citations (Upcoming)
*(To be populated upon Phase 4 execution)*

---

## 4. Phase 5 Results: Ragas & Grounding Metrics (Upcoming)
*(To be populated upon Phase 5 execution)*

---

## 5. Phase 6 Results: Policy Gate Decisions (Upcoming)
*(To be populated upon Phase 6 execution)*

---

## 6. Phase 7 & 8 Results: Opik Cloud Traces & End-to-End Scorecard (Upcoming)
*(To be populated upon Phase 7 & 8 execution)*
