"""
Domain Models for Technical Documents, Revisions, and Access Control (ACL).
"""
from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field

class DocumentType(str, Enum):
    TECHNICAL_SPECIFICATION = "technical_specification"
    MANUAL = "manual"
    DATASHEET = "datasheet"
    SERVICE_RECORD = "service_record"
    STANDARD = "standard"
    DRAWING = "drawing"
    OTHER = "other"

class DocumentClassification(str, Enum):
    PUBLIC_INTERNAL = "public_internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"

class RevisionApprovalStatus(str, Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    OBSOLETE = "obsolete"

class DocumentRevision(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str = Field(default_factory=lambda: str(uuid4()))
    document_id: str
    revision_code: str  # e.g., "Rev. 02"
    revision_number: int = 1
    effective_at: Optional[datetime] = None
    supersedes_revision_id: Optional[str] = None
    approval_status: RevisionApprovalStatus = RevisionApprovalStatus.DRAFT
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    parser_name: str = "docling"
    parser_version: str = "2.120.3"
    source_sha256: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Document(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str = Field(default_factory=lambda: str(uuid4()))
    document_number: Optional[str] = None
    title: str
    filename: str
    mime_type: str = "application/pdf"
    file_size: int
    sha256: str
    document_type: DocumentType = DocumentType.TECHNICAL_SPECIFICATION
    language: str = "tr"
    department_id: str
    equipment_ids: List[str] = Field(default_factory=list)
    classification: DocumentClassification = DocumentClassification.PUBLIC_INTERNAL
    status: str = "ready"  # "uploaded" | "processing" | "ready" | "failed" | "archived"
    current_revision_id: Optional[str] = None
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = None
