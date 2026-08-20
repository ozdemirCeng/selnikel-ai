from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class DocumentMetadata(BaseModel):
    document_id: str
    document_version: int = 1
    filename: str
    file_hash: str  # SHA-256 for deduplication
    file_size_bytes: int
    content_type: str
    document_type: str = "technical_specification"
    department: str = "engineering"
    language: str = "tr"
    total_pages: Optional[int] = None
    status: DocumentStatus = DocumentStatus.PENDING
    error_message: Optional[str] = None


class ChunkMetadata(BaseModel):
    chunk_id: str
    document_id: str
    document_version: int = 1
    filename: str
    page_number: int = 1
    section: Optional[str] = None
    document_type: str = "technical_specification"
    department: str = "engineering"
    equipment_ids: List[str] = Field(default_factory=list)
    classification: str = "public_internal"
    approval_status: str = "approved"
    revision_id: Optional[str] = None
    revision_number: Optional[int] = None
    revision_code: Optional[str] = None
    language: str = "tr"
    chunk_index: int = 0
    token_count: Optional[int] = None


class DomainChunk(BaseModel):
    content: str
    metadata: ChunkMetadata
