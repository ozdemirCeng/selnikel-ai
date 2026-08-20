"""
Formal Domain Contracts for RAG Evaluation, Metrics, Evidence, and Grounding.
Maintains single-source-of-truth definitions aligned with app.domain.rag and app.domain.document.
"""
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.domain.rag import Citation, RetrievalResult


class AbstentionReason(str, Enum):
    OUT_OF_DOMAIN = "out_of_domain"
    INSUFFICIENT_CONTEXT = "insufficient_context"
    OBSOLETE_REVISION = "obsolete_revision"
    SAFETY_AMBIGUITY = "safety_ambiguity"
    NONE = "none"


class ExpectedEvidence(BaseModel):
    document_name: str
    document_sha256: Optional[str] = None
    revision_code: Optional[str] = None
    page_number: int
    section: Optional[str] = None
    expected_numerical_parameters: List[str] = Field(default_factory=list)
    ground_truth_answer: str


class BenchmarkQuestion(BaseModel):
    id: str
    category: str
    question: str
    expected_evidence: ExpectedEvidence
    is_safety_critical: bool = False
    is_out_of_domain: bool = False
    expert_reviewer: Optional[str] = None
    dataset_version: str = "1.0.0"
    anonymized: bool = True


class RetrievedEvidence(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    page_number: int
    section: Optional[str] = None
    content_snippet: str
    score: float

    @classmethod
    def from_retrieval_result(cls, res: RetrievalResult) -> "RetrievedEvidence":
        return cls(
            chunk_id=res.chunk_id,
            document_id=res.metadata.document_id,
            filename=res.metadata.filename,
            page_number=res.metadata.page_number,
            section=res.metadata.section,
            content_snippet=res.content[:250],
            score=res.score,
        )


class MetricResult(BaseModel):
    recall_at_5: float = Field(ge=0.0, le=1.0)
    ndcg_at_5: float = Field(ge=0.0, le=1.0)
    numerical_unit_accuracy: float = Field(ge=0.0, le=1.0)
    citation_precision: float = Field(ge=0.0, le=1.0)
    faithfulness_score: float = Field(ge=0.0, le=1.0)
    abstention_accuracy: float = Field(ge=0.0, le=1.0)
    safety_compliance_score: float = Field(ge=0.0, le=1.0)
    overall_score: float = Field(ge=0.0, le=1.0)


class EvaluationItemResult(BaseModel):
    question_id: str
    category: str
    question: str
    metrics: MetricResult
    generated_answer: str
    citations: List[Citation] = Field(default_factory=list)
    retrieved_evidence: List[RetrievedEvidence] = Field(default_factory=list)
    passed: bool


class EvaluationRunReport(BaseModel):
    run_id: str
    dataset_version: str
    prompt_version: str
    model_name: str
    executed_at: str
    total_questions: int
    passed_questions: int
    mean_recall_at_5: float
    mean_ndcg_at_5: float
    mean_numerical_unit_accuracy: float
    mean_citation_precision: float
    mean_faithfulness: float
    safety_compliance_rate: float
    abstention_rate: float
    item_results: List[EvaluationItemResult] = Field(default_factory=list)
