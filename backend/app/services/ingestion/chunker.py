import math
import re
import uuid
from typing import List, Optional
from app.core.logging import logger
from app.domain.document import ChunkMetadata, DomainChunk
from app.domain.parser import ParsedBlockType, ParsedDocument, ParsedPage, ParsedTable


class TableAwareChunker:
    """Structure-aware chunker that preserves Markdown table integrity,
    inherits hierarchical section headings, and tracks exact page provenance.
    """

    def __init__(
        self,
        max_chunk_chars: int = 2400,  # ~600 tokens (avg 4 chars/token)
        chunk_overlap_chars: int = 400,  # ~100 tokens
        prepend_section_headers: bool = True,
    ):
        self.max_chunk_chars = max_chunk_chars
        self.chunk_overlap_chars = chunk_overlap_chars
        self.prepend_section_headers = prepend_section_headers

    def chunk_document(
        self,
        parsed_doc: ParsedDocument,
        document_id: str,
        document_version: int = 1,
        document_type: str = "technical_specification",
        department: str = "engineering",
        language: str = "tr",
    ) -> List[DomainChunk]:
        """Split a ParsedDocument into a list of enriched DomainChunk instances."""
        chunks: List[DomainChunk] = []
        chunk_index = 0

        # If document has explicit pages, chunk page-by-page to guarantee page provenance
        if parsed_doc.pages:
            for page in parsed_doc.pages:
                page_chunks = self._chunk_page(
                    page=page,
                    parsed_doc=parsed_doc,
                    document_id=document_id,
                    document_version=document_version,
                    document_type=document_type,
                    department=department,
                    language=language,
                    start_index=chunk_index,
                )
                chunks.extend(page_chunks)
                chunk_index += len(page_chunks)
        else:
            # Fallback for documents without explicit pages
            dummy_page = ParsedPage(
                page_number=1,
                text_content=parsed_doc.full_markdown,
                tables=parsed_doc.tables,
            )
            chunks = self._chunk_page(
                page=dummy_page,
                parsed_doc=parsed_doc,
                document_id=document_id,
                document_version=document_version,
                document_type=document_type,
                department=department,
                language=language,
                start_index=0,
            )

        logger.info(
            f"Chunked document '{parsed_doc.filename}' into {len(chunks)} structure-aware chunks."
        )
        return chunks

    def _chunk_page(
        self,
        page: ParsedPage,
        parsed_doc: ParsedDocument,
        document_id: str,
        document_version: int,
        document_type: str,
        department: str,
        language: str,
        start_index: int,
    ) -> List[DomainChunk]:
        chunks: List[DomainChunk] = []
        current_index = start_index

        # 1. Process Page Tables as Atomic Chunks First
        for table in page.tables:
            table_content = table.markdown_table
            if table.caption:
                table_content = f"### Table: {table.caption}\n\n{table_content}"

            section_context = (
                f"[Document: {parsed_doc.filename} | Page: {page.page_number} | Type: Table]\n\n"
            )
            full_content = section_context + table_content

            chunk_id = str(uuid.uuid4())
            metadata = ChunkMetadata(
                chunk_id=chunk_id,
                document_id=document_id,
                document_version=document_version,
                filename=parsed_doc.filename,
                page_number=page.page_number,
                section="Table: " + (table.caption or "Data Table"),
                document_type=document_type,
                department=department,
                language=language,
                chunk_index=current_index,
                token_count=math.ceil(len(full_content) / 4),
            )
            chunks.append(DomainChunk(content=full_content, metadata=metadata))
            current_index += 1

        # 2. Process Page Text Content
        text = page.text_content.strip()
        if not text:
            return chunks

        # Extract current section header context
        current_section = "General"
        if page.section_headers:
            current_section = " > ".join(page.section_headers[:2])

        # Split text into paragraphs
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        current_block = ""

        for para in paragraphs:
            # Check if adding this paragraph exceeds maximum chunk size
            if len(current_block) + len(para) + 2 > self.max_chunk_chars:
                if current_block:
                    chunks.append(
                        self._create_text_chunk(
                            raw_text=current_block,
                            page_number=page.page_number,
                            filename=parsed_doc.filename,
                            section=current_section,
                            document_id=document_id,
                            document_version=document_version,
                            document_type=document_type,
                            department=department,
                            language=language,
                            chunk_index=current_index,
                        )
                    )
                    current_index += 1
                    # Retain overlap from end of previous block
                    overlap_point = max(0, len(current_block) - self.chunk_overlap_chars)
                    current_block = current_block[overlap_point:].strip()
                    if current_block:
                        current_block += "\n\n" + para
                    else:
                        current_block = para
                else:
                    # Single oversized paragraph: split into slices
                    for slice_text in self._split_oversized_text(para, self.max_chunk_chars):
                        chunks.append(
                            self._create_text_chunk(
                                raw_text=slice_text,
                                page_number=page.page_number,
                                filename=parsed_doc.filename,
                                section=current_section,
                                document_id=document_id,
                                document_version=document_version,
                                document_type=document_type,
                                department=department,
                                language=language,
                                chunk_index=current_index,
                            )
                        )
                        current_index += 1
                    current_block = ""
            else:
                if current_block:
                    current_block += "\n\n" + para
                else:
                    current_block = para

        if current_block.strip():
            chunks.append(
                self._create_text_chunk(
                    raw_text=current_block,
                    page_number=page.page_number,
                    filename=parsed_doc.filename,
                    section=current_section,
                    document_id=document_id,
                    document_version=document_version,
                    document_type=document_type,
                    department=department,
                    language=language,
                    chunk_index=current_index,
                )
            )

        return chunks

    def _create_text_chunk(
        self,
        raw_text: str,
        page_number: int,
        filename: str,
        section: str,
        document_id: str,
        document_version: int,
        document_type: str,
        department: str,
        language: str,
        chunk_index: int,
    ) -> DomainChunk:
        if self.prepend_section_headers:
            header_prefix = (
                f"[Document: {filename} | Page: {page_number} | Section: {section}]\n\n"
            )
            full_content = header_prefix + raw_text
        else:
            full_content = raw_text

        chunk_id = str(uuid.uuid4())
        metadata = ChunkMetadata(
            chunk_id=chunk_id,
            document_id=document_id,
            document_version=document_version,
            filename=filename,
            page_number=page_number,
            section=section,
            document_type=document_type,
            department=department,
            language=language,
            chunk_index=chunk_index,
            token_count=math.ceil(len(full_content) / 4),
        )
        return DomainChunk(content=full_content, metadata=metadata)

    def _split_oversized_text(self, text: str, max_chars: int) -> List[str]:
        """Split an excessively long paragraph at sentence boundaries."""
        sentences = re.split(r"(?<=[.!?])\s+", text)
        slices: List[str] = []
        current = ""

        for s in sentences:
            if len(current) + len(s) + 1 > max_chars:
                if current:
                    slices.append(current)
                    current = s
                else:
                    # Single sentence exceeds max_chars: hard slice
                    for i in range(0, len(s), max_chars):
                        slices.append(s[i : i + max_chars])
                    current = ""
            else:
                if current:
                    current += " " + s
                else:
                    current = s

        if current.strip():
            slices.append(current)
        return slices


# Default singleton instance
table_aware_chunker = TableAwareChunker()
