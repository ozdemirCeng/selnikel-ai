from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ParsedBlockType(str, Enum):
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    TABLE = "table"
    LIST_ITEM = "list_item"
    CODE = "code"
    IMAGE = "image"
    OTHER = "other"


class ParsedBlock(BaseModel):
    content: str
    block_type: ParsedBlockType = ParsedBlockType.PARAGRAPH
    page_number: int = 1
    section_header: Optional[str] = None
    bbox: Optional[List[float]] = None  # [x0, y0, x1, y1] if available


class ParsedTable(BaseModel):
    table_id: str
    page_number: int = 1
    markdown_table: str
    caption: Optional[str] = None
    num_rows: int = 0
    num_cols: int = 0
    headers: List[str] = Field(default_factory=list)


class ParsedPage(BaseModel):
    page_number: int
    text_content: str
    tables: List[ParsedTable] = Field(default_factory=list)
    section_headers: List[str] = Field(default_factory=list)


class ParsedDocument(BaseModel):
    filename: str
    total_pages: int
    full_markdown: str
    pages: List[ParsedPage] = Field(default_factory=list)
    tables: List[ParsedTable] = Field(default_factory=list)
    blocks: List[ParsedBlock] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    parser_name: str = "docling"
