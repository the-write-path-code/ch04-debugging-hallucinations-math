"""Deterministic retrieval implementation and ranking metric calculations."""

import math
import re

from ch04_eval.schemas import (
    DeterministicMetrics,
    DocumentChunk,
    RetrievalResult,
    RetrievedChunk,
)


def tokenize(text: str) -> list[str]:
    """Simple alphanumeric tokenizer with lowercase normalization."""
    return re.findall(r"\b[a-zA-Z0-9_\$#\.\-]+\b", text.lower())


class BM25Retriever:
    """Okapi BM25 retriever for local corpus indexing and ranked search."""

    def __init__(
        self,
        chunks: list[DocumentChunk],
        k1: float = 1.5,
        b: float = 0.75,
        corpus_version: str = "2026.1",
    ):
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.corpus_version = corpus_version

        # Index construction
        self.corpus_size = len(chunks)
        self.doc_len: list[int] = []
        self.doc_freqs: list[dict[str, int]] = []
        self.idf: dict[str, float] = {}

        self._build_index()

    def _build_index(self) -> None:
        """Compute term frequencies, document lengths, and inverse document frequencies."""
        df: dict[str, int] = {}
        total_length = 0

        for chunk in self.chunks:
            tokens = tokenize(chunk.text)
            length = len(tokens)
            self.doc_len.append(length)
            total_length += length

            freqs: dict[str, int] = {}
            for token in tokens:
                freqs[token] = freqs.get(token, 0) + 1
            self.doc_freqs.append(freqs)

            for token in freqs:
                df[token] = df.get(token, 0) + 1

        self.avg_doc_len = (total_length / self.corpus_size) if self.corpus_size > 0 else 1.0

        # Calculate Okapi IDF with smoothing
        for term, count in df.items():
            # Standard Okapi BM25 formula
            self.idf[term] = math.log(1.0 + (self.corpus_size - count + 0.5) / (count + 0.5))

    def retrieve(self, query: str, top_k: int = 5) -> RetrievalResult:
        """Search corpus chunks and return top_k ranked results."""
        query_tokens = tokenize(query)
        scores: list[float] = [0.0] * self.corpus_size

        if not query_tokens or self.corpus_size == 0:
            return RetrievalResult(
                query=query,
                retrieved_chunks=[],
                corpus_version=self.corpus_version,
            )

        for i, freqs in enumerate(self.doc_freqs):
            score = 0.0
            doc_len = self.doc_len[i]
            for q_term in query_tokens:
                if q_term not in freqs:
                    continue
                tf = freqs[q_term]
                idf = self.idf.get(q_term, 0.1)
                numerator = tf * (self.k1 + 1.0)
                denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_len))
                score += idf * (numerator / denominator)

            scores[i] = score

        # Rank documents by score descending
        ranked_indices = sorted(range(self.corpus_size), key=lambda idx: scores[idx], reverse=True)
        top_indices = ranked_indices[:top_k]

        retrieved_chunks: list[RetrievedChunk] = []
        for rank, idx in enumerate(top_indices, start=1):
            chunk = self.chunks[idx]
            retrieved_chunks.append(
                RetrievedChunk(
                    document_id=chunk.document_id,
                    chunk_id=chunk.chunk_id,
                    text=chunk.text,
                    rank=rank,
                    retrieval_score=round(float(scores[idx]), 4),
                    retrieval_method="bm25_okapi",
                )
            )

        return RetrievalResult(
            query=query,
            retrieved_chunks=retrieved_chunks,
            corpus_version=self.corpus_version,
        )


def compute_recall_at_k(
    retrieved_doc_ids: list[str],
    relevant_doc_ids: list[str],
    k: int = 5,
) -> float:
    """Calculate Recall@K: proportion of relevant documents found in top-K retrieved items.

    Returns 0.0 if relevant_doc_ids is empty.
    """
    if not relevant_doc_ids:
        return 0.0

    unique_relevant = set(relevant_doc_ids)
    top_k_retrieved = set(retrieved_doc_ids[:k])
    hits = unique_relevant.intersection(top_k_retrieved)
    return round(len(hits) / len(unique_relevant), 4)


def compute_precision_at_k(
    retrieved_doc_ids: list[str],
    relevant_doc_ids: list[str],
    k: int = 5,
) -> float:
    """Calculate Precision@K: proportion of top-K retrieved items that are relevant."""
    if k <= 0 or not relevant_doc_ids:
        return 0.0

    unique_relevant = set(relevant_doc_ids)
    top_k_retrieved = set(retrieved_doc_ids[:k])
    hits = unique_relevant.intersection(top_k_retrieved)
    return round(len(hits) / k, 4)


def compute_mrr(
    retrieved_doc_ids: list[str],
    relevant_doc_ids: list[str],
) -> float:
    """Calculate Mean Reciprocal Rank (MRR): 1 / rank of first relevant document."""
    if not relevant_doc_ids or not retrieved_doc_ids:
        return 0.0

    unique_relevant = set(relevant_doc_ids)
    for rank, doc_id in enumerate(retrieved_doc_ids, start=1):
        if doc_id in unique_relevant:
            return round(1.0 / rank, 4)

    return 0.0


def compute_deterministic_metrics(
    retrieval_result: RetrievalResult,
    relevant_doc_ids: list[str],
    k: int = 5,
) -> DeterministicMetrics:
    """Compute consolidated deterministic ranking metrics for a retrieval run."""
    retrieved_doc_ids = [chunk.document_id for chunk in retrieval_result.retrieved_chunks]

    return DeterministicMetrics(
        recall_at_k=compute_recall_at_k(retrieved_doc_ids, relevant_doc_ids, k=k),
        precision_at_k=compute_precision_at_k(retrieved_doc_ids, relevant_doc_ids, k=k),
        mrr=compute_mrr(retrieved_doc_ids, relevant_doc_ids),
        k=k,
    )
