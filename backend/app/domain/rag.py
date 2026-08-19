from typing import List, Optional
from pydantic import BaseModel, Field
from app.domain.document import ChunkMetadata


class Citation(BaseModel):
    document_id: str
    filename: str
    page_number: int
    section: Optional[str] = None
    snippet: str
    score: Optional[float] = None


class RetrievalFilter(BaseModel):
    department: Optional[str] = None
    department_ids: Optional[List[str]] = None
    allowed_departments: Optional[List[str]] = None
    document_type: Optional[str] = None
    document_id: Optional[str] = None
    equipment_ids: Optional[List[str]] = None
    approval_status: Optional[str] = "approved"
    revision_policy: Optional[str] = "approved_latest"
    language: Optional[str] = None


class RetrievalResult(BaseModel):
    chunk_id: str
    content: str
    metadata: ChunkMetadata
    score: float


class GenerationOutput(BaseModel):
    answer: str
    citations: List[Citation] = Field(default_factory=list)
    sources_used: List[str] = Field(default_factory=list)
