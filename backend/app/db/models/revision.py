"""
SQLAlchemy 2.0 ORM Models for Document Revisions and Access Control Lists (ACL).
"""
from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    ForeignKey,
    Text,
    Index,
)
from app.db.base import Base

def gen_uuid():
    return str(uuid.uuid4())

class DocumentRevisionModel(Base):
    __tablename__ = "document_revisions"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    revision_code = Column(String(50), nullable=False)  # "Rev. 01"
    revision_number = Column(Integer, nullable=False, default=1)
    effective_at = Column(DateTime(timezone=True), nullable=True)
    supersedes_revision_id = Column(String(36), ForeignKey("document_revisions.id"), nullable=True)
    approval_status = Column(String(50), nullable=False, default="draft", index=True)  # "draft" | "review" | "approved" | "obsolete"
    approved_by = Column(String(36), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    obsoleted_at = Column(DateTime(timezone=True), nullable=True)
    parser_name = Column(String(100), nullable=False, default="docling")
    parser_version = Column(String(50), nullable=False, default="2.120.3")
    source_sha256 = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index(
            "uq_document_single_approved_revision",
            "document_id",
            unique=True,
            postgresql_where=(approval_status == "approved"),
            sqlite_where=(approval_status == "approved"),
        ),
    )


class DocumentACLModel(Base):
    __tablename__ = "document_acl"

    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True)
    department_id = Column(String(36), primary_key=True)
    permission = Column(String(50), nullable=False, default="read")  # "read" | "write"
