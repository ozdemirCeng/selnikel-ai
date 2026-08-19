"""
Domain Models for Structural Document Elements and Retrieval Chunks.
Replaces flat chunks with hierarchical document elements (sections, tables, formulas, warnings).
"""
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from uuid import uuid4
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field

class ElementType(str, Enum):
    SECTION = "section"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    TABLE_ROW = "table_row"
    FIGURE = "figure"
    CAPTION = "caption"
    PROCEDURE_STEP = "procedure_step"
    WARNING = "warning"
    FORMULA = "formula"

class BoundingBox(BaseModel):
    page: int
    x: float
    y: float
    w: float
    h: float

class DocumentElement(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str = Field(default_factory=lambda: str(uuid4()))
    document_id: str
    revision_id: str
    parent_id: Optional[str] = None
    element_type: ElementType
    sequence: int
    page_start: int
    page_end: int
    section_path: List[str] = Field(default_factory=list)
    content: str
    structured_content: Dict[str, Any] = Field(default_factory=dict)
    bounding_boxes: List[BoundingBox] = Field(default_factory=list)
    equipment_ids: List[str] = Field(default_factory=list)
    standard_references: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class RetrievalChunk(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str = Field(default_factory=lambda: str(uuid4()))
    document_element_id: str
    document_id: str
    revision_id: str
    content: str
    content_hash: str
    token_count: int
    embedding_model: str = "BAAI/bge-m3"
    embedding_model_version: str = "v1.0"
    index_version: str = "v2.0"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
