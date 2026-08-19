"""
SQLAlchemy 2.0 ORM Model for Hierarchical Document Elements.
"""
from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    ForeignKey,
    JSON,
    Text,
)
from app.db.base import Base

def gen_uuid():
    return str(uuid.uuid4())

class DocumentElementModel(Base):
    __tablename__ = "document_elements"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    revision_id = Column(String(36), ForeignKey("document_revisions.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = Column(String(36), ForeignKey("document_elements.id"), nullable=True)
    element_type = Column(String(50), nullable=False, index=True)  # "section", "table", "paragraph", "warning", etc.
    sequence = Column(Integer, nullable=False, default=1)
    page_start = Column(Integer, nullable=False, default=1)
    page_end = Column(Integer, nullable=False, default=1)
    section_path = Column(JSON, nullable=False, default=[])
    content = Column(Text, nullable=False)
    structured_content = Column(JSON, nullable=False, default={})
    bounding_boxes = Column(JSON, nullable=False, default=[])
    equipment_ids = Column(JSON, nullable=False, default=[])
    standard_references = Column(JSON, nullable=False, default=[])
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
