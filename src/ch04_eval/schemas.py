"""Pydantic schemas and enums for RAG evaluation, grounding, and policy gates."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RiskTier(str, Enum):
    """Risk tier of a question / domain."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PolicyDecision(str, Enum):
    """Final decision produced by the deterministic policy gate."""

    ANSWER = "ANSWER"
    QUALIFIED_ANSWER = "QUALIFIED_ANSWER"
    ABSTAIN = "ABSTAIN"
    BLOCK = "BLOCK"
    HUMAN_REVIEW = "HUMAN_REVIEW"


class SufficiencyClass(str, Enum):
    """Judge evaluation of whether retrieved evidence suffices to answer the question."""

    SUFFICIENT = "SUFFICIENT"
    PARTIAL = "PARTIAL"
    INSUFFICIENT = "INSUFFICIENT"
    CONFLICTING = "CONFLICTING"


class ClaimVerdict(str, Enum):
    """Grounding verdict for an individual atomic claim against retrieved evidence."""

    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class DocumentChunk(BaseModel):
    """A single ingested corpus chunk."""

    document_id: str
    chunk_id: str
    title: str = ""
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievedChunk(BaseModel):
    """A ranked retrieved chunk returned by a search query."""

    document_id: str
    chunk_id: str
    text: str
    rank: int
    retrieval_score: float
    retrieval_method: str = "bm25_dense_hybrid"


class RetrievalResult(BaseModel):
    """Full structured retrieval result for a query."""

    query: str
    retrieved_chunks: list[RetrievedChunk]
    corpus_version: str = "2026.1"


class GoldenTestCase(BaseModel):
    """A single golden evaluation test case."""

    id: str
    question: str
    expected_answer: str
    expected_facts: str
    relevant_document_ids: list[str] = Field(default_factory=list)
    risk_tier: RiskTier = RiskTier.LOW
    should_answer: str = "True"  # "True", "False", or "partial"
    notes: str = ""


class GenerationResult(BaseModel):
    """Structured response from the LLM generator."""

    answer: str
    citations: list[str] = Field(default_factory=list)
    model: str
    prompt_version: str = "v1"


class ClaimAnalysis(BaseModel):
    """Grounding check for an atomic claim."""

    claim: str
    verdict: ClaimVerdict
    evidence_chunk_ids: list[str] = Field(default_factory=list)
    rationale: str = ""


class GroundingResult(BaseModel):
    """Aggregate claim-level grounding evaluation."""

    claims: list[ClaimAnalysis] = Field(default_factory=list)
    supported_claims: int = 0
    unsupported_claims: int = 0
    contradicted_claims: int = 0
    claim_grounding_rate: float = 1.0
    judge_model: str = ""
    prompt_version: str = "v1"


class SufficiencyResult(BaseModel):
    """Evidence sufficiency judge verdict."""

    sufficiency_class: SufficiencyClass
    rationale: str = ""
    judge_model: str = ""


class DeterministicMetrics(BaseModel):
    """Deterministic ranking metrics computed against golden document IDs."""

    recall_at_k: float = 0.0
    precision_at_k: float = 0.0
    mrr: float = 0.0
    k: int = 5


class RagasMetrics(BaseModel):
    """Standard RAG metric vocabulary scores."""

    context_precision: float | None = None
    context_recall: float | None = None
    faithfulness: float | None = None
    answer_relevance: float | None = None


class PolicyDecisionResult(BaseModel):
    """Output from the policy gate."""

    decision: PolicyDecision
    decision_reason: str
    metrics_used: dict[str, Any] = Field(default_factory=dict)
    threshold_version: str = "v1.0"
    corpus_version: str = "2026.1"
    evaluation_run_id: str = ""


class EvaluationCaseResult(BaseModel):
    """Consolidated end-to-end evaluation record for a single test case."""

    case_id: str
    question: str
    risk_tier: RiskTier
    expected_answer: str
    retrieval: RetrievalResult
    deterministic_metrics: DeterministicMetrics
    generation: GenerationResult
    ragas_metrics: RagasMetrics
    grounding: GroundingResult
    sufficiency: SufficiencyResult
    policy_decision: PolicyDecisionResult
