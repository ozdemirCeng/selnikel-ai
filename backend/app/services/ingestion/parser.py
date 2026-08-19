import os
import re
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.core.logging import logger
from app.domain.parser import (
    ParsedBlock,
    ParsedBlockType,
    ParsedDocument,
    ParsedPage,
    ParsedTable,
)


class BaseDocumentParser(ABC):
    """Abstract interface for all document parsing engines in Selnikel AI."""

    @abstractmethod
    async def parse(self, file_path: str, content_type: Optional[str] = None) -> ParsedDocument:
        """Parse a document file into structured ParsedDocument with page-level attribution."""
        pass

    @abstractmethod
    def supports(self, file_path: str, content_type: Optional[str] = None) -> bool:
        """Check if this parser supports the given file format."""
        pass


class FastFallbackParser(BaseDocumentParser):
    """Lightweight, resilient fallback parser handling plain text, markdown, CSV, and PDFs.
    Guarantees that document parsing never crashes even in resource-constrained environments.
    """

    SUPPORTED_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".log", ".pdf"}

    def supports(self, file_path: str, content_type: Optional[str] = None) -> bool:
        ext = Path(file_path).suffix.lower()
        if ext in self.SUPPORTED_EXTENSIONS:
            return True
        if content_type and any(
            t in content_type.lower()
            for t in ["text/plain", "text/markdown", "text/csv", "application/pdf"]
        ):
            return True
        return False

    async def parse(self, file_path: str, content_type: Optional[str] = None) -> ParsedDocument:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Document file not found: {file_path}")

        filename = path.name
        ext = path.suffix.lower()

        if ext == ".pdf" or (content_type and "pdf" in content_type.lower()):
            return self._parse_pdf(path)
        else:
            return self._parse_text(path)

    def _parse_pdf(self, path: Path) -> ParsedDocument:
        try:
            import pypdf

            reader = pypdf.PdfReader(str(path))
            total_pages = len(reader.pages)
            pages: List[ParsedPage] = []
            blocks: List[ParsedBlock] = []
            all_text_parts: List[str] = []

            for idx, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text() or ""
                cleaned_text = page_text.strip()
                all_text_parts.append(f"<!-- Page {idx} -->\n{cleaned_text}")

                # Extract potential section headers (lines starting with uppercase/numbers)
                section_headers = []
                for line in cleaned_text.splitlines():
                    line_str = line.strip()
                    if line_str and (
                        line_str.startswith("#")
                        or re.match(r"^[0-9]+(\.[0-9]+)*\s+[A-Z]", line_str)
                    ):
                        section_headers.append(line_str)

                pages.append(
                    ParsedPage(
                        page_number=idx,
                        text_content=cleaned_text,
                        tables=[],
                        section_headers=section_headers,
                    )
                )

                if cleaned_text:
                    blocks.append(
                        ParsedBlock(
                            content=cleaned_text,
                            block_type=ParsedBlockType.PARAGRAPH,
                            page_number=idx,
                        )
                    )

            full_markdown = "\n\n".join(all_text_parts)
            return ParsedDocument(
                filename=path.name,
                total_pages=max(1, total_pages),
                full_markdown=full_markdown,
                pages=pages,
                tables=[],
                blocks=blocks,
                metadata={"file_size_bytes": path.stat().st_size},
                parser_name="fast_fallback_pypdf",
            )
        except Exception as e:
            logger.error(f"FastFallbackParser PDF extraction failed: {e}")
            raise

    def _parse_text(self, path: Path) -> ParsedDocument:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        # Detect markdown tables in text
        tables = self._extract_markdown_tables(content)
        total_pages = 1

        page = ParsedPage(
            page_number=1,
            text_content=content,
            tables=tables,
            section_headers=[
                line.strip()
                for line in content.splitlines()
                if line.strip().startswith("#")
            ],
        )

        return ParsedDocument(
            filename=path.name,
            total_pages=total_pages,
            full_markdown=content,
            pages=[page],
            tables=tables,
            blocks=[
                ParsedBlock(
                    content=content,
                    block_type=ParsedBlockType.PARAGRAPH,
                    page_number=1,
                )
            ],
            metadata={"file_size_bytes": path.stat().st_size},
            parser_name="fast_fallback_text",
        )

    def _extract_markdown_tables(self, content: str) -> List[ParsedTable]:
        tables: List[ParsedTable] = []
        table_pattern = re.compile(
            r"(\|[^\n]+\|\r?\n\|[-:\s|]+\|\r?\n(?:\|[^\n]+\|\r?\n?)+)", re.MULTILINE
        )
        for match in table_pattern.finditer(content):
            table_md = match.group(0).strip()
            lines = [l.strip() for l in table_md.splitlines() if l.strip()]
            if len(lines) >= 3:
                headers = [c.strip() for c in lines[0].split("|")[1:-1]]
                tables.append(
                    ParsedTable(
                        table_id=str(uuid.uuid4()),
                        page_number=1,
                        markdown_table=table_md,
                        num_rows=len(lines) - 2,
                        num_cols=len(headers),
                        headers=headers,
                    )
                )
        return tables


class DoclingParser(BaseDocumentParser):
    """Advanced industrial document parser using IBM Docling for structural layout
    and table extraction. Preserves technical tables in GitHub-Flavored Markdown.
    """

    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".html", ".asciidoc", ".md"}

    def __init__(self):
        self._converter = None
        self._docling_available = False
        self._init_docling()

    def _init_docling(self) -> None:
        try:
            from docling.document_converter import DocumentConverter

            self._converter = DocumentConverter()
            self._docling_available = True
            logger.info("Docling DocumentConverter initialized successfully.")
        except ImportError:
            self._docling_available = False
            logger.warning(
                "Docling package not installed. Parser will automatically route to FastFallbackParser."
            )
        except Exception as e:
            self._docling_available = False
            logger.warning(f"Docling initialization error: {e}. Fallback enabled.")

    @property
    def is_available(self) -> bool:
        return self._docling_available

    def supports(self, file_path: str, content_type: Optional[str] = None) -> bool:
        ext = Path(file_path).suffix.lower()
        return ext in self.SUPPORTED_EXTENSIONS

    async def parse(self, file_path: str, content_type: Optional[str] = None) -> ParsedDocument:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Document file not found: {file_path}")

        # If Docling is not available, delegate seamlessly to fallback
        if not self._docling_available:
            logger.info(f"Docling unavailable, delegating {path.name} to FastFallbackParser")
            fallback = FastFallbackParser()
            return await fallback.parse(file_path, content_type)

        try:
            from docling.datamodel.base_models import InputFormat

            conv_result = self._converter.convert(str(path))
            doc = conv_result.document

            full_markdown = doc.export_to_markdown()
            pages_dict: Dict[int, List[str]] = {}
            tables: List[ParsedTable] = []
            blocks: List[ParsedBlock] = []

            # Extract tables directly from Docling structure
            if hasattr(doc, "tables") and doc.tables:
                for t_idx, table_item in enumerate(doc.tables):
                    page_no = 1
                    if hasattr(table_item, "prov") and table_item.prov:
                        page_no = getattr(table_item.prov[0], "page_no", 1)

                    table_md = table_item.export_to_markdown() if hasattr(table_item, "export_to_markdown") else str(table_item)
                    tables.append(
                        ParsedTable(
                            table_id=str(uuid.uuid4()),
                            page_number=page_no,
                            markdown_table=table_md,
                            caption=getattr(table_item, "caption", None),
                        )
                    )

            # Extract hierarchical items with page attribution
            total_pages = 1
            if hasattr(doc, "pages") and doc.pages:
                total_pages = len(doc.pages)

            if hasattr(doc, "iterate_items"):
                for item, level in doc.iterate_items():
                    text = getattr(item, "text", "") or ""
                    page_no = 1
                    if hasattr(item, "prov") and item.prov:
                        page_no = getattr(item.prov[0], "page_no", 1)
                        total_pages = max(total_pages, page_no)

                    if page_no not in pages_dict:
                        pages_dict[page_no] = []
                    pages_dict[page_no].append(text)

                    b_type = ParsedBlockType.PARAGRAPH
                    item_type = type(item).__name__.lower()
                    if "header" in item_type or "title" in item_type or "heading" in item_type:
                        b_type = ParsedBlockType.HEADING
                    elif "table" in item_type:
                        b_type = ParsedBlockType.TABLE
                    elif "list" in item_type:
                        b_type = ParsedBlockType.LIST_ITEM
                    elif "code" in item_type:
                        b_type = ParsedBlockType.CODE

                    blocks.append(
                        ParsedBlock(
                            content=text,
                            block_type=b_type,
                            page_number=page_no,
                        )
                    )

            # Assemble pages
            pages: List[ParsedPage] = []
            for p_num in range(1, total_pages + 1):
                p_text = "\n".join(pages_dict.get(p_num, []))
                p_tables = [t for t in tables if t.page_number == p_num]
                pages.append(
                    ParsedPage(
                        page_number=p_num,
                        text_content=p_text,
                        tables=p_tables,
                    )
                )

            return ParsedDocument(
                filename=path.name,
                total_pages=total_pages,
                full_markdown=full_markdown,
                pages=pages,
                tables=tables,
                blocks=blocks,
                metadata={"file_size_bytes": path.stat().st_size},
                parser_name="docling_layout_parser",
            )

        except Exception as e:
            logger.warning(f"Docling parsing failed for {path.name}: {e}. Falling back to FastFallbackParser.")
            fallback = FastFallbackParser()
            return await fallback.parse(file_path, content_type)


class DocumentParserFactory:
    """Factory to resolve and provide the optimal document parser."""

    _docling_parser: Optional[DoclingParser] = None
    _fallback_parser: Optional[FastFallbackParser] = None

    @classmethod
    def get_parser(
        cls,
        file_path: str,
        content_type: Optional[str] = None,
        prefer_docling: bool = True,
    ) -> BaseDocumentParser:
        if prefer_docling:
            if cls._docling_parser is None:
                cls._docling_parser = DoclingParser()
            if cls._docling_parser.supports(file_path, content_type):
                return cls._docling_parser

        if cls._fallback_parser is None:
            cls._fallback_parser = FastFallbackParser()
        return cls._fallback_parser


# Default singleton instance
document_parser_factory = DocumentParserFactory
