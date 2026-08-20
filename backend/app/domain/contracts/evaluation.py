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


class LocatorType(str, Enum):
    TABLE_CELL = "table_cell"
    SECTION_TEXT = "section_text"


class EvidenceLocator(BaseModel):
    locator_type: LocatorType
    table_id: Optional[str] = None
    row_key: Optional[str] = None
    column_name: Optional[str] = None
    section_header: Optional[str] = None
    key_phrase: Optional[str] = None


class ExpectedEvidence(BaseModel):
    document_name: str
    document_sha256: Optional[str] = None
    revision_code: Optional[str] = None
    page_number: int
    section: Optional[str] = None
    locator: Optional[EvidenceLocator] = None
    expected_numerical_parameters: List[str] = Field(default_factory=list)
    ground_truth_answer: str


class BenchmarkQuestion(BaseModel):
    id: str
    category: str
    question: str
    expected_evidence: Optional[ExpectedEvidence] = None
    is_safety_critical: bool = False
    is_out_of_domain: bool = False
    abstention_expected: Optional[bool] = None
    expected_abstention_reason: Optional[AbstentionReason] = None
    expert_reviewer: Optional[str] = None
    dataset_version: str = "1.0.0"
    anonymized: bool = True
    synthetic: bool = True
    review_status: str = "unverified_draft"


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
    execution_mode: str = "self-check"
    status: str = "COMPLETED"
    gate_status: str = "PENDING"  # PASSED, FAILED, SKIPPED
    gate_failure_reasons: List[str] = Field(default_factory=list)
    dataset_version: str = "1.0.0"
    prompt_version: str = "1.2.0"
    prompt_sha256: Optional[str] = None
    dataset_sha256: Optional[str] = None
    manifest_sha256: Optional[str] = None
    git_commit: Optional[str] = None
    model_name: str = "evaluator"
    oracle_mock_used: bool = False
    network_access: str = "disabled"
    executed_at: str
    duration_seconds: float = 0.0
    total_questions: int = 0
    passed_questions: int = 0
    mean_recall_at_5: float = 0.0
    mean_ndcg_at_5: float = 0.0
    mean_numerical_unit_accuracy: float = 0.0
    mean_citation_precision: float = 0.0
    mean_faithfulness: float = 0.0
    safety_compliance_rate: float = 0.0
    abstention_rate: float = 0.0
    item_results: List[EvaluationItemResult] = Field(default_factory=list)
