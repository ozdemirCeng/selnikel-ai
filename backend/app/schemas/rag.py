from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CitationSchema(BaseModel):
    document_id: str
    filename: str
    page_number: int
    section: Optional[str] = None
    snippet: str
    score: Optional[float] = None


class RAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=2, description="The technical question or search query")
    department: Optional[str] = Field(default=None, description="Filter by department (e.g. engineering)")
    document_type: Optional[str] = Field(default=None, description="Filter by doc type")
    document_id: Optional[str] = Field(default=None, description="Filter by specific document")
    language: Optional[str] = Field(default=None, description="Filter by language code")
    top_k: int = Field(default=4, ge=1, le=20, description="Number of retrieved chunks")


class RAGQueryResponse(BaseModel):
    answer: str
    query: str
    citations: List[CitationSchema] = Field(default_factory=list)
    sources_used: List[str] = Field(default_factory=list)
    latency_ms: float
    llm_provider: str
    llm_model: str


class QueryLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    query_text: str
    generated_answer: Optional[str] = None
    retrieved_chunk_ids: Optional[List[str]] = None
    citations: Optional[List[Dict[str, Any]]] = None
    latency_ms: Optional[float] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    created_at: datetime
