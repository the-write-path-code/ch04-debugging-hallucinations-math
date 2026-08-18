"""Script to ingest the policy corpus and display chunk metadata."""

import os
import sys

from ch04_eval.config import get_settings
from ch04_eval.ingest import load_corpus


def main() -> None:
    settings = get_settings()
    corpus_path = settings.corpus_path

    print(f"Ingesting corpus from: {corpus_path}")
    if not os.path.exists(corpus_path):
        print(f"Error: Corpus file not found at {corpus_path}", file=sys.stderr)
        sys.exit(1)

    chunks = load_corpus(corpus_path)
    print(f"Successfully parsed {len(chunks)} chunks across distinct policy documents:\n")

    doc_counts: dict[str, int] = {}
    for c in chunks:
        doc_counts[c.document_id] = doc_counts.get(c.document_id, 0) + 1

    for doc_id, count in sorted(doc_counts.items()):
        print(f"  - Document {doc_id}: {count} chunk(s)")

    print(f"\nTotal Chunks: {len(chunks)}")


if __name__ == "__main__":
    main()
