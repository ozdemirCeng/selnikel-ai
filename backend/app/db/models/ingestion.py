"""
SQLAlchemy 2.0 ORM Model for Asynchronous Ingestion Jobs.
"""
from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
)
from app.db.base import Base

def gen_uuid():
    return str(uuid.uuid4())

class IngestionJobModel(Base):
    __tablename__ = "ingestion_jobs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    revision_id = Column(String(36), ForeignKey("document_revisions.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=True)
    file_path = Column(String(500), nullable=True)
    department_id = Column(String(50), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    sha256_hash = Column(String(64), nullable=True)

    state = Column(String(50), nullable=False, default="queued", index=True)
    progress = Column(Float, nullable=False, default=0.0)
    attempt = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    dead_letter = Column(Boolean, nullable=False, default=False, index=True)
    next_attempt_at = Column(DateTime(timezone=True), nullable=True)

    worker_lease_id = Column(String(100), nullable=True)
    lease_expires_at = Column(DateTime(timezone=True), nullable=True)
    chunks_count = Column(Integer, nullable=True)

    error_code = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
