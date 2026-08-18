"""Unit tests for ingestion, BM25 retrieval, and deterministic ranking metrics."""

from ch04_eval.ingest import load_corpus, parse_markdown_corpus
from ch04_eval.retrieval import (
    BM25Retriever,
    compute_deterministic_metrics,
    compute_mrr,
    compute_precision_at_k,
    compute_recall_at_k,
)
from ch04_eval.schemas import RetrievalResult, RetrievedChunk


def test_compute_recall_at_k_fixed_fixtures():
    """Verify Recall@K mathematical behavior against known inputs."""
    retrieved = ["docA", "docB", "docC", "docD", "docE"]

    # Full recall: all relevant documents are in top 5
    assert compute_recall_at_k(retrieved, ["docA", "docB"], k=5) == 1.0

    # Partial recall: only 1 of 2 in top 2
    assert compute_recall_at_k(retrieved, ["docA", "docC"], k=2) == 0.5

    # Zero recall
    assert compute_recall_at_k(retrieved, ["docZ"], k=5) == 0.0

    # Empty relevant doc list returns 0.0 without crashing
    assert compute_recall_at_k(retrieved, [], k=5) == 0.0


def test_compute_precision_at_k_fixed_fixtures():
    """Verify Precision@K mathematical behavior against known inputs."""
    retrieved = ["docA", "docB", "docC", "docD", "docE"]

    # 2 out of 5 are relevant
    assert compute_precision_at_k(retrieved, ["docA", "docB"], k=5) == 0.4

    # 1 out of 2 are relevant
    assert compute_precision_at_k(retrieved, ["docA"], k=2) == 0.5

    # Zero precision
    assert compute_precision_at_k(retrieved, ["docZ"], k=5) == 0.0

    # k = 0 returns 0.0
    assert compute_precision_at_k(retrieved, ["docA"], k=0) == 0.0


def test_compute_mrr_fixed_fixtures():
    """Verify Mean Reciprocal Rank (MRR) for ranks 1, 2, 3, and not found."""
    retrieved = ["docA", "docB", "docC", "docD"]

    # Rank 1 -> 1 / 1 = 1.0
    assert compute_mrr(retrieved, ["docA"]) == 1.0

    # Rank 2 -> 1 / 2 = 0.5
    assert compute_mrr(retrieved, ["docB"]) == 0.5

    # Rank 3 -> 1 / 3 = 0.3333
    assert compute_mrr(retrieved, ["docC"]) == 0.3333

    # Not found -> 0.0
    assert compute_mrr(retrieved, ["docZ"]) == 0.0

    # Empty retrieved or relevant
    assert compute_mrr([], ["docA"]) == 0.0
    assert compute_mrr(retrieved, []) == 0.0


def test_ingest_and_chunk_parsing():
    """Verify markdown corpus parsing extracts structured chunks with metadata."""
    sample_text = """# Policy Manual
Corpus Version: 2026.1

## Document: SEC-2026-01 (Security)
[doc_id: SEC-2026-01]
### Section 1: Customer Retention
Data must be retained for 7 years.

### Section 2: Passwords
Passwords must be 16 characters.
"""
    chunks = parse_markdown_corpus(sample_text)
    assert len(chunks) == 2
    assert chunks[0].document_id == "SEC-2026-01"
    assert chunks[0].chunk_id == "SEC-2026-01#001"
    assert "7 years" in chunks[0].text
    assert chunks[1].chunk_id == "SEC-2026-01#002"
    assert chunks[1].metadata["document_title"] == "SEC-2026-01 (Security)"


def test_bm25_retriever_ranking_on_real_corpus():
    """Verify BM25Retriever accurately retrieves and ranks relevant chunks."""
    chunks = load_corpus("data/source/sample_policy_corpus.md")
    assert len(chunks) >= 20

    retriever = BM25Retriever(chunks)

    # Search for core collaboration hours
    res = retriever.retrieve("What are the core collaboration hours for remote employees?", top_k=5)
    assert len(res.retrieved_chunks) == 5
    assert res.retrieved_chunks[0].document_id == "HR-2026-01"
    assert "10:00 AM to 3:00 PM" in res.retrieved_chunks[0].text

    # Search for customer data retention period
    res2 = retriever.retrieve("How long must customer transactional records be retained?", top_k=5)
    assert res2.retrieved_chunks[0].document_id == "SEC-2026-01"
    assert "7 years" in res2.retrieved_chunks[0].text


def test_compute_deterministic_metrics_helper():
    """Verify compute_deterministic_metrics aggregates metrics into DeterministicMetrics."""
    retrieval_res = RetrievalResult(
        query="test query",
        retrieved_chunks=[
            RetrievedChunk(
                document_id="SEC-2026-01",
                chunk_id="SEC-2026-01#001",
                text="",
                rank=1,
                retrieval_score=1.5,
            ),
            RetrievedChunk(
                document_id="HR-2026-01",
                chunk_id="HR-2026-01#001",
                text="",
                rank=2,
                retrieval_score=1.2,
            ),
        ],
        corpus_version="2026.1",
    )
    metrics = compute_deterministic_metrics(retrieval_res, relevant_doc_ids=["SEC-2026-01"], k=2)
    assert metrics.recall_at_k == 1.0
    assert metrics.precision_at_k == 0.5
    assert metrics.mrr == 1.0
    assert metrics.k == 2
