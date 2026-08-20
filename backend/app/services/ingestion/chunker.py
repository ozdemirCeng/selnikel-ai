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
    Guarantees:
    - Tables are NEVER split mid-row.
    - Large tables that span multiple chunks repeat their header rows and context.
    - Every chunk preserves document_id, filename, revision, page_number, and section breadcrumbs.
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

        # Extract current section header context for page
        current_section = "General"
        if page.section_headers:
            current_section = " > ".join(page.section_headers[:2])

        # 1. Process Page Tables with Layout Fidelity
        for table in page.tables:
            table_chunks = self._chunk_table_atomic(
                table=table,
                page_number=page.page_number,
                filename=parsed_doc.filename,
                section=current_section,
                document_id=document_id,
                document_version=document_version,
                document_type=document_type,
                department=department,
                language=language,
                start_index=current_index,
            )
            chunks.extend(table_chunks)
            current_index += len(table_chunks)

        # 2. Process Page Text Content
        text = page.text_content.strip()
        if not text:
            return chunks

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

    def _chunk_table_atomic(
        self,
        table: ParsedTable,
        page_number: int,
        filename: str,
        section: str,
        document_id: str,
        document_version: int,
        document_type: str,
        department: str,
        language: str,
        start_index: int,
    ) -> List[DomainChunk]:
        """
        Chunks a Markdown table preserving header rows and never splitting mid-row.
        If table is smaller than max_chunk_chars, emits 1 atomic chunk.
        If oversized, slices rows with header repetition.
        """
        chunks: List[DomainChunk] = []
        table_lines = [l.strip() for l in table.markdown_table.strip().splitlines() if l.strip()]

        header_prefix = f"### Table: {table.caption or 'Technical Parameters'}\n\n" if table.caption else ""
        section_context = f"[Document: {filename} | Page: {page_number} | Section: {section} | Type: Table]\n\n"

        full_table_content = section_context + header_prefix + table.markdown_table

        # Case 1: Fits comfortably in a single chunk
        if len(full_table_content) <= self.max_chunk_chars or len(table_lines) <= 2:
            chunk_id = str(uuid.uuid4())
            metadata = ChunkMetadata(
                chunk_id=chunk_id,
                document_id=document_id,
                document_version=document_version,
                filename=filename,
                page_number=page_number,
                section=f"{section} > Table: {table.caption or 'Data Table'}",
                document_type=document_type,
                department=department,
                language=language,
                chunk_index=start_index,
                token_count=math.ceil(len(full_table_content) / 4),
            )
            return [DomainChunk(content=full_table_content, metadata=metadata)]

        # Case 2: Multi-row table exceeding max_chunk_chars -> Slice rows with header repetition
        header_line = table_lines[0]
        sep_line = table_lines[1]
        body_rows = table_lines[2:]

        current_rows: List[str] = []
        part_num = 1
        idx = start_index

        for row in body_rows:
            test_table = "\n".join([header_line, sep_line] + current_rows + [row])
            test_content = section_context + f"{header_prefix}(Part {part_num})\n\n" + test_table

            if len(test_content) > self.max_chunk_chars and current_rows:
                slice_table_str = "\n".join([header_line, sep_line] + current_rows)
                slice_content = section_context + f"{header_prefix}(Part {part_num})\n\n" + slice_table_str

                chunk_id = str(uuid.uuid4())
                metadata = ChunkMetadata(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    document_version=document_version,
                    filename=filename,
                    page_number=page_number,
                    section=f"{section} > Table: {table.caption or 'Data Table'} (Part {part_num})",
                    document_type=document_type,
                    department=department,
                    language=language,
                    chunk_index=idx,
                    token_count=math.ceil(len(slice_content) / 4),
                )
                chunks.append(DomainChunk(content=slice_content, metadata=metadata))
                idx += 1
                part_num += 1
                current_rows = [row]
            else:
                current_rows.append(row)

        if current_rows:
            slice_table_str = "\n".join([header_line, sep_line] + current_rows)
            slice_content = section_context + f"{header_prefix}(Part {part_num})\n\n" + slice_table_str

            chunk_id = str(uuid.uuid4())
            metadata = ChunkMetadata(
                chunk_id=chunk_id,
                document_id=document_id,
                document_version=document_version,
                filename=filename,
                page_number=page_number,
                section=f"{section} > Table: {table.caption or 'Data Table'} (Part {part_num})",
                document_type=document_type,
                department=department,
                language=language,
                chunk_index=idx,
                token_count=math.ceil(len(slice_content) / 4),
            )
            chunks.append(DomainChunk(content=slice_content, metadata=metadata))

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
        """Helper to create a standard text chunk with structured contextual header."""
        header = ""
        if self.prepend_section_headers:
            header = f"[Document: {filename} | Page: {page_number} | Section: {section}]\n\n"

        full_content = header + raw_text
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
        """Safely split an oversized paragraph by sentences or word boundaries."""
        sentences = re.split(r"(?<=[.!?])\s+", text)
        slices: List[str] = []
        curr = ""

        for s in sentences:
            if len(curr) + len(s) + 1 > max_chars:
                if curr:
                    slices.append(curr.strip())
                curr = s
            else:
                curr = f"{curr} {s}".strip() if curr else s

        if curr.strip():
            slices.append(curr.strip())

        return slices or [text[:max_chars]]


table_aware_chunker = TableAwareChunker()
