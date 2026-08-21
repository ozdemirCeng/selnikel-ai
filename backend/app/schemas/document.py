from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    file_hash: str
    file_size_bytes: int
    content_type: str
    document_type: str
    department: str
    language: str
    version: int
    total_pages: Optional[int] = None
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DocumentUploadResponse(BaseModel):
    document: DocumentResponse
    chunk_count: int
    is_duplicate: bool = False
    message: str


class DocumentListResponse(BaseModel):
    items: List[DocumentResponse]
    total: int


class ChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., alias="chunk_id")
    document_id: str
    chunk_index: int
    page_number: int
    section: Optional[str] = None
    content: str
    token_count: Optional[int] = None


class MessageResponse(BaseModel):
    message: str
    success: bool = True


class WebSearchRequest(BaseModel):
    query: str
    max_results: int = Field(5, ge=1, le=10)


class WebSearchResult(BaseModel):
    title: str
    href: str
    body: str


class WebSearchResponse(BaseModel):
    query: str
    results: List[WebSearchResult]
    total: int


class WebUrlIngestRequest(BaseModel):
    url: str
    department: str = "engineering"
    document_type: str = "technical_specification"
    language: str = "tr"
    custom_title: Optional[str] = None


class RawTextIngestRequest(BaseModel):
    title: str
    content: str
    department: str = "engineering"
    document_type: str = "technical_specification"
    language: str = "tr"

