"""Corpus ingestion and chunking for policy documents."""

import os
import re

from ch04_eval.schemas import DocumentChunk


def parse_markdown_corpus(corpus_text: str, corpus_version: str = "2026.1") -> list[DocumentChunk]:
    """Parse structured markdown corpus into discrete DocumentChunk objects.

    Splits on markdown document headers (## Document:) and section headers (### Section).
    Extracts [doc_id: ...], section titles, and status notices (e.g., SUPERSEDED, ACTIVE).
    """
    chunks: list[DocumentChunk] = []

    # Detect corpus version from header if present
    version_match = re.search(r"^Corpus Version:\s*(.+)$", corpus_text, re.MULTILINE)
    if version_match:
        corpus_version = version_match.group(1).strip()

    # Split into document blocks
    doc_blocks = re.split(r"\n(?=## Document:)", corpus_text)

    for doc_block in doc_blocks:
        doc_block = doc_block.strip()
        if not doc_block or not doc_block.startswith("## Document:"):
            continue

        # Extract Document ID and Title
        doc_id_match = re.search(r"\[doc_id:\s*([A-Za-z0-9_-]+)\]", doc_block)
        doc_title_match = re.search(r"^## Document:\s*([^\n]+)", doc_block, re.MULTILINE)

        if not doc_id_match:
            continue

        doc_id = doc_id_match.group(1).strip()
        doc_title = doc_title_match.group(1).strip() if doc_title_match else doc_id

        # Check for document-level status notices (e.g. SUPERSEDED, ACTIVE, CONFLICTING)
        status_notice = ""
        status_match = re.search(r"### Status Notice:\s*([^\n]+)", doc_block)
        if status_match:
            status_notice = status_match.group(1).strip()

        # Split into section blocks
        section_blocks = re.split(r"\n(?=### Section)", doc_block)
        section_index = 0

        for sec_block in section_blocks:
            sec_block = sec_block.strip()
            if not sec_block.startswith("### Section"):
                continue

            section_index += 1
            chunk_id = f"{doc_id}#{section_index:03d}"

            # Extract section title and text
            lines = sec_block.splitlines()
            sec_title = lines[0].replace("### ", "").strip()
            body_text = "\n".join(lines[1:]).strip()

            metadata = {
                "document_id": doc_id,
                "document_title": doc_title,
                "section_title": sec_title,
                "status_notice": status_notice,
                "corpus_version": corpus_version,
            }

            chunks.append(
                DocumentChunk(
                    document_id=doc_id,
                    chunk_id=chunk_id,
                    title=f"{doc_title} - {sec_title}",
                    text=f"Document: {doc_title}\nSection: {sec_title}\n{body_text}",
                    metadata=metadata,
                )
            )

    return chunks


def load_corpus(corpus_path: str = "data/source/sample_policy_corpus.md") -> list[DocumentChunk]:
    """Load and ingest markdown policy corpus from disk."""
    if not os.path.exists(corpus_path):
        raise FileNotFoundError(f"Corpus file not found: {corpus_path}")

    with open(corpus_path, "r", encoding="utf-8") as f:
        content = f.read()

    return parse_markdown_corpus(content)
