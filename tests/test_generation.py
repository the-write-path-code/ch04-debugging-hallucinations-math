"""Unit tests for generation module, citation parsing, and prompt templates."""

import pytest

from ch04_eval.config import Settings, get_settings
from ch04_eval.generation import (
    GENERATION_PROMPT_VERSION,
    OllamaGenerator,
    extract_citations,
    format_context_blocks,
    generate_answer,
)
from ch04_eval.schemas import RetrievedChunk


def test_extract_citations_valid_and_deduplicated():
    """Verify regex correctly parses [doc_id#chunk_num] citations and deduplicates."""
    text = (
        "Under policy [HR-2026-01#001], core hours are 10 AM to 3 PM. "
        "Also per [HR-2026-01#001], Friday is deep work. "
        "See also [SEC-2026-01#003] and invalid citation [not_a_chunk]."
    )
    citations = extract_citations(text)
    assert citations == ["HR-2026-01#001", "SEC-2026-01#003"]


def test_extract_citations_empty_when_no_citations():
    """Verify empty list returned when no citations exist."""
    text = "The policy does not contain information on this topic."
    assert extract_citations(text) == []


def test_format_context_blocks():
    """Verify context formatting includes chunk IDs and scores."""
    chunks = [
        RetrievedChunk(
            document_id="SEC-2026-01",
            chunk_id="SEC-2026-01#001",
            text="Customer data retained for 7 years.",
            rank=1,
            retrieval_score=0.925,
        ),
        RetrievedChunk(
            document_id="HR-2026-01",
            chunk_id="HR-2026-01#001",
            text="Core hours 10 AM to 3 PM.",
            rank=2,
            retrieval_score=0.812,
        ),
    ]
    formatted = format_context_blocks(chunks)
    assert "[SEC-2026-01#001] (Score: 0.925)" in formatted
    assert "Customer data retained for 7 years." in formatted
    assert "[HR-2026-01#001] (Score: 0.812)" in formatted


def test_mock_generation_offline():
    """Verify mock generation works without requiring network or API keys."""
    settings = Settings(ollama_api_key=None, _env_file=None)
    mock_resp = "Core collaboration hours are 10:00 AM to 3:00 PM [HR-2026-01#001]."

    res = generate_answer(
        question="What are the core hours?",
        retrieved_chunks=[],
        settings=settings,
        mock_response=mock_resp,
    )
    assert res.answer == mock_resp
    assert res.citations == ["HR-2026-01#001"]
    assert res.prompt_version == GENERATION_PROMPT_VERSION
    assert res.model.startswith("mock-")


def test_generator_raises_when_missing_key_and_no_mock():
    """Verify generator validates API key when mock is not provided."""
    settings = Settings(ollama_api_key=None, _env_file=None)
    generator = OllamaGenerator(settings=settings)

    with pytest.raises(ValueError, match="OLLAMA_API_KEY is required"):
        generator.generate(
            question="What are the core hours?",
            retrieved_chunks=[],
        )


@pytest.mark.skipif(
    not get_settings().has_ollama_key(),
    reason="OLLAMA_API_KEY not configured in .env; skipping live Ollama Cloud integration test",
)
def test_live_ollama_cloud_generation():
    """Opt-in live integration test for Ollama Cloud."""
    generator = OllamaGenerator()
    chunks = [
        RetrievedChunk(
            document_id="SEC-2026-01",
            chunk_id="SEC-2026-01#001",
            text="Document: SEC-2026-01 (Information Security & Data Retention)\nSection: Customer Data Retention\nAll customer transactional logs and personally identifiable information (PII) must be retained in encrypted cold storage for exactly 7 years from the date of account closure.",
            rank=1,
            retrieval_score=1.0,
        )
    ]
    result = generator.generate(
        question="How long must customer transactional logs be retained?",
        retrieved_chunks=chunks,
    )
    assert len(result.answer) > 0
    assert "7" in result.answer
    assert "SEC-2026-01#001" in result.citations
