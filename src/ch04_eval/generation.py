"""Grounded answer generation using Ollama Cloud with citation enforcement."""

import logging
import re

import ollama

from ch04_eval.config import Settings, get_settings
from ch04_eval.schemas import GenerationResult, RetrievedChunk

logger = logging.getLogger(__name__)

GENERATION_PROMPT_VERSION = "2026.1-v1"

SYSTEM_PROMPT = """You are a precise corporate policy assistant for Acme Corporation.
Answer the user's question using ONLY the provided context excerpts.

Rules:
1. Ground your answer exclusively on the facts stated in the provided context.
2. For every factual claim you make, cite the source chunk using the exact format [doc_id#chunk_num] (for example: [SEC-2026-01#001] or [FIN-2026-03#001]).
3. If the provided context does not contain sufficient facts to answer the question, or if the question is about a topic not mentioned in the context, clearly state: "The provided policy documentation does not contain information regarding [topic]." Do not guess or invent facts.
4. If the context contains a SUPERSEDED or inactive policy alongside an ACTIVE policy, rely only on the ACTIVE policy and explicitly clarify the replacement.
5. If the context contains a CONFLICTING clause for a specific department or team, state the specific exception clearly.
6. Keep the response concise, factual, and strictly grounded.
"""

USER_PROMPT_TEMPLATE = """Context Excerpts:
{context_blocks}

Question: {question}

Grounded Answer with Citations:"""


def format_context_blocks(retrieved_chunks: list[RetrievedChunk]) -> str:
    """Format retrieved chunks into indexed context blocks with chunk IDs."""
    if not retrieved_chunks:
        return "No relevant context found."

    blocks = []
    for chunk in retrieved_chunks:
        blocks.append(f"[{chunk.chunk_id}] (Score: {chunk.retrieval_score:.3f})\n{chunk.text}\n")
    return "\n---\n".join(blocks)


def extract_citations(text: str) -> list[str]:
    """Extract chunk citations matching pattern [doc_id#chunk_num] or [doc_id]."""
    citations = re.findall(r"\[([A-Za-z0-9_-]+#[0-9]{3})\]", text)
    seen = set()
    unique_citations = []
    for c in citations:
        if c not in seen:
            seen.add(c)
            unique_citations.append(c)
    return unique_citations


class OllamaGenerator:
    """Generator client interacting with Ollama Cloud API."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.base_url = self.settings.ollama_base_url.rstrip("/")
        self.model = self.settings.get_effective_model()
        self.api_key = self.settings.ollama_api_key

    def generate(
        self,
        question: str,
        retrieved_chunks: list[RetrievedChunk],
        mock_response: str | None = None,
    ) -> GenerationResult:
        """Generate a grounded response for a question and retrieved chunks."""
        if mock_response is not None:
            citations = extract_citations(mock_response)
            return GenerationResult(
                answer=mock_response,
                citations=citations,
                model=f"mock-{self.model}",
                prompt_version=GENERATION_PROMPT_VERSION,
            )

        # Validate configuration before making network call
        self.settings.validate_ollama()

        context_blocks = format_context_blocks(retrieved_chunks)
        user_content = USER_PROMPT_TEMPLATE.format(
            context_blocks=context_blocks,
            question=question,
        )

        try:
            client = ollama.Client(
                host=self.base_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            response = client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                options={
                    "temperature": 0.0,
                    "top_p": 0.9,
                },
            )
            answer = response.message.content.strip()
            citations = extract_citations(answer)

            return GenerationResult(
                answer=answer,
                citations=citations,
                model=self.model,
                prompt_version=GENERATION_PROMPT_VERSION,
            )
        except Exception as e:
            logger.error(f"Ollama Cloud generation failed: {e}")
            raise RuntimeError(f"Ollama Cloud generation error: {e}") from e


def generate_answer(
    question: str,
    retrieved_chunks: list[RetrievedChunk],
    settings: Settings | None = None,
    mock_response: str | None = None,
) -> GenerationResult:
    """Convenience functional wrapper for answer generation."""
    generator = OllamaGenerator(settings=settings)
    return generator.generate(question, retrieved_chunks, mock_response=mock_response)
