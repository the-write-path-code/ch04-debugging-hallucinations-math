"""Claim-level grounding extraction, verdict classification, and evidence sufficiency evaluation."""

import json
import logging
import re

import ollama

from ch04_eval.config import Settings, get_settings
from ch04_eval.schemas import (
    ClaimAnalysis,
    ClaimVerdict,
    GroundingResult,
    RetrievedChunk,
    SufficiencyClass,
    SufficiencyResult,
)

logger = logging.getLogger(__name__)

GROUNDING_PROMPT_VERSION = "2026.1-v1"

CLAIM_EXTRACTION_PROMPT = """You are an NLP judge specializing in factual claim decomposition.
Given an assistant's answer to a user question, extract all distinct atomic factual claims.

Rules:
1. Break compound sentences into standalone declarative claims.
2. Ignore meta-discourse (such as "The policy states that...", "As an assistant...", "Under section...").
3. If the answer states that the policy does not contain information or abstains, return a single claim stating the abstention.
4. Output JSON strictly matching this schema:
{
  "claims": ["claim 1", "claim 2"]
}
"""

CLAIM_VERDICT_SYSTEM_PROMPT = """You are a rigorous factual verification judge.
Evaluate each atomic claim against the provided evidence excerpts.

For each claim, assign exactly one verdict:
- SUPPORTED: The claim is directly stated or explicitly entailed by the evidence chunks.
- UNSUPPORTED: The claim introduces details, figures, or facts not present in the evidence.
- CONTRADICTED: The claim directly conflicts with or is refuted by the evidence.
- NOT_APPLICABLE: The claim is a statement of abstention ("policy does not mention X"), opinion, or conversational filler.

Output JSON format strictly:
{
  "results": [
    {
      "claim": "claim text",
      "verdict": "SUPPORTED" | "UNSUPPORTED" | "CONTRADICTED" | "NOT_APPLICABLE",
      "evidence_chunk_ids": ["doc#001"],
      "rationale": "one sentence explanation"
    }
  ]
}
"""

SUFFICIENCY_SYSTEM_PROMPT = """You are an evidence evaluation judge.
Determine if the provided retrieved evidence chunks contain sufficient information to answer the user's question safely and completely.

Classification options:
- SUFFICIENT: The retrieved evidence contains all facts required for a complete, accurate answer.
- PARTIAL: The evidence contains some relevant facts but is missing critical aspects requested by the question.
- INSUFFICIENT: The evidence contains no relevant information or does not address the question.
- CONFLICTING: The evidence contains contradictory rules or conflicting policy guidelines for different groups.

Output JSON strictly:
{
  "sufficiency_class": "SUFFICIENT" | "PARTIAL" | "INSUFFICIENT" | "CONFLICTING",
  "rationale": "concise explanation"
}
"""


def split_atomic_claims_fallback(text: str) -> list[str]:
    """Rule-based atomic claim splitter for offline/fallback mode."""
    # Remove citations
    clean_text = re.sub(r"\[[A-Za-z0-9_-]+(?:#[0-9]{3})?\]", "", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+", clean_text)
    claims = [s.strip() for s in sentences if len(s.strip()) > 10 and not s.strip().startswith("#")]
    return claims or [clean_text]


class GroundingJudge:
    """Judge model client for claim extraction, verdict classification, and sufficiency."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.base_url = self.settings.ollama_base_url.rstrip("/")
        self.judge_model = self.settings.get_effective_judge_model()
        self.api_key = self.settings.ollama_api_key

    def _call_judge_json(self, system_prompt: str, user_content: str) -> dict:
        """Execute a JSON-enforced chat completion with Ollama Cloud."""
        self.settings.validate_ollama()
        client = ollama.Client(
            host=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        response = client.chat(
            model=self.judge_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            format="json",
            options={"temperature": 0.0},
        )
        content = response.message.content.strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Attempt to locate JSON inside markdown code block if present
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            raise

    def extract_claims(self, question: str, answer: str) -> list[str]:
        """Extract atomic claims from generated answer."""
        if not self.settings.has_ollama_key():
            return split_atomic_claims_fallback(answer)

        try:
            prompt = f"Question: {question}\nAnswer: {answer}"
            data = self._call_judge_json(CLAIM_EXTRACTION_PROMPT, prompt)
            claims = data.get("claims", [])
            return [str(c).strip() for c in claims if str(c).strip()] or split_atomic_claims_fallback(answer)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Judge claim extraction failed ({e}), using rule-based fallback.")
            return split_atomic_claims_fallback(answer)

    def evaluate_grounding(
        self,
        question: str,
        answer: str,
        retrieved_chunks: list[RetrievedChunk],
        mock_claims: list[ClaimAnalysis] | None = None,
    ) -> GroundingResult:
        """Classify claims and calculate claim grounding rate."""
        if mock_claims is not None:
            supported = sum(1 for c in mock_claims if c.verdict == ClaimVerdict.SUPPORTED)
            unsupported = sum(1 for c in mock_claims if c.verdict == ClaimVerdict.UNSUPPORTED)
            contradicted = sum(1 for c in mock_claims if c.verdict == ClaimVerdict.CONTRADICTED)
            denom = supported + unsupported + contradicted
            rate = (supported / denom) if denom > 0 else 1.0

            return GroundingResult(
                claims=mock_claims,
                supported_claims=supported,
                unsupported_claims=unsupported,
                contradicted_claims=contradicted,
                claim_grounding_rate=round(rate, 4),
                judge_model=f"mock-{self.judge_model}",
                prompt_version=GROUNDING_PROMPT_VERSION,
            )

        claims = self.extract_claims(question, answer)
        if not claims:
            return GroundingResult(
                claims=[],
                supported_claims=0,
                unsupported_claims=0,
                contradicted_claims=0,
                claim_grounding_rate=1.0,
                judge_model=self.judge_model,
                prompt_version=GROUNDING_PROMPT_VERSION,
            )

        context_text = "\n\n".join(f"[{c.chunk_id}]: {c.text}" for c in retrieved_chunks)
        user_prompt = f"Evidence Excerpts:\n{context_text}\n\nClaims to verify:\n" + "\n".join(
            f"- {c}" for c in claims
        )

        try:
            data = self._call_judge_json(CLAIM_VERDICT_SYSTEM_PROMPT, user_prompt)
            raw_results = data.get("results", [])
            claim_analyses: list[ClaimAnalysis] = []

            for item in raw_results:
                raw_verdict = str(item.get("verdict", "UNSUPPORTED")).upper()
                try:
                    verdict = ClaimVerdict(raw_verdict)
                except ValueError:
                    verdict = ClaimVerdict.UNSUPPORTED

                claim_analyses.append(
                    ClaimAnalysis(
                        claim=str(item.get("claim", "")),
                        verdict=verdict,
                        evidence_chunk_ids=item.get("evidence_chunk_ids", []),
                        rationale=str(item.get("rationale", "")),
                    )
                )

            supported = sum(1 for c in claim_analyses if c.verdict == ClaimVerdict.SUPPORTED)
            unsupported = sum(1 for c in claim_analyses if c.verdict == ClaimVerdict.UNSUPPORTED)
            contradicted = sum(1 for c in claim_analyses if c.verdict == ClaimVerdict.CONTRADICTED)
            denom = supported + unsupported + contradicted
            rate = (supported / denom) if denom > 0 else 1.0

            return GroundingResult(
                claims=claim_analyses,
                supported_claims=supported,
                unsupported_claims=unsupported,
                contradicted_claims=contradicted,
                claim_grounding_rate=round(rate, 4),
                judge_model=self.judge_model,
                prompt_version=GROUNDING_PROMPT_VERSION,
            )
        except Exception as e:
            logger.error(f"Judge grounding evaluation failed: {e}")
            raise RuntimeError(f"Grounding judge error: {e}") from e

    def evaluate_sufficiency(
        self,
        question: str,
        retrieved_chunks: list[RetrievedChunk],
        mock_result: SufficiencyResult | None = None,
    ) -> SufficiencyResult:
        """Classify evidence sufficiency into SUFFICIENT, PARTIAL, INSUFFICIENT, or CONFLICTING."""
        if mock_result is not None:
            return mock_result

        if not retrieved_chunks:
            return SufficiencyResult(
                sufficiency_class=SufficiencyClass.INSUFFICIENT,
                rationale="No context chunks were retrieved for the query.",
                judge_model=self.judge_model,
            )

        context_text = "\n\n".join(f"[{c.chunk_id}]: {c.text}" for c in retrieved_chunks)
        user_prompt = f"Question: {question}\n\nEvidence Excerpts:\n{context_text}"

        try:
            data = self._call_judge_json(SUFFICIENCY_SYSTEM_PROMPT, user_prompt)
            raw_class = str(data.get("sufficiency_class", "INSUFFICIENT")).upper()
            try:
                suff_class = SufficiencyClass(raw_class)
            except ValueError:
                suff_class = SufficiencyClass.INSUFFICIENT

            return SufficiencyResult(
                sufficiency_class=suff_class,
                rationale=str(data.get("rationale", "")),
                judge_model=self.judge_model,
            )
        except Exception as e:
            logger.error(f"Sufficiency judge failed: {e}")
            raise RuntimeError(f"Sufficiency judge error: {e}") from e


def evaluate_grounding(
    question: str,
    answer: str,
    retrieved_chunks: list[RetrievedChunk],
    settings: Settings | None = None,
    mock_claims: list[ClaimAnalysis] | None = None,
) -> GroundingResult:
    """Convenience function for claim grounding evaluation."""
    judge = GroundingJudge(settings=settings)
    return judge.evaluate_grounding(question, answer, retrieved_chunks, mock_claims=mock_claims)


def evaluate_sufficiency(
    question: str,
    retrieved_chunks: list[RetrievedChunk],
    settings: Settings | None = None,
    mock_result: SufficiencyResult | None = None,
) -> SufficiencyResult:
    """Convenience function for evidence sufficiency evaluation."""
    judge = GroundingJudge(settings=settings)
    return judge.evaluate_sufficiency(question, retrieved_chunks, mock_result=mock_result)
