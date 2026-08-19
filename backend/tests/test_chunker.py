import pytest
from app.domain.parser import ParsedBlock, ParsedBlockType, ParsedDocument, ParsedPage, ParsedTable
from app.services.ingestion.chunker import TableAwareChunker


def test_table_aware_chunker_preserves_table_and_all_9_metadata_fields():
    chunker = TableAwareChunker()

    sample_table = ParsedTable(
        table_id="tbl_001",
        page_number=3,
        markdown_table="| Parameter | Value |\n| :--- | :--- |\n| Steam Capacity | 5000 kg/h |\n| Design Pressure | 16 bar |",
        caption="Boiler Design Parameters",
        num_rows=2,
        num_cols=2,
        headers=["Parameter", "Value"],
    )

    page1 = ParsedPage(
        page_number=1,
        text_content="# Introduction\n\nSelnikel industrial boilers provide high efficiency steam generation.",
        tables=[],
        section_headers=["# Introduction"],
    )

    page3 = ParsedPage(
        page_number=3,
        text_content="### Operating Parameters\n\nRefer to the following table for nominal operation limits.",
        tables=[sample_table],
        section_headers=["### Operating Parameters"],
    )

    parsed_doc = ParsedDocument(
        filename="SB_Series_Datasheet.pdf",
        total_pages=3,
        full_markdown="",
        pages=[page1, page3],
        tables=[sample_table],
        blocks=[],
    )

    chunks = chunker.chunk_document(
        parsed_doc=parsed_doc,
        document_id="doc_test_123",
        document_version=2,
        document_type="technical_datasheet",
        department="engineering",
        language="tr",
    )

    assert len(chunks) >= 2

    # Verify Table Chunk
    table_chunks = [c for c in chunks if "Table" in c.metadata.section]
    assert len(table_chunks) == 1
    t_chunk = table_chunks[0]

    # Verify 9 Mandatory Metadata Fields
    assert t_chunk.metadata.document_id == "doc_test_123"
    assert t_chunk.metadata.document_version == 2
    assert t_chunk.metadata.filename == "SB_Series_Datasheet.pdf"
    assert t_chunk.metadata.page_number == 3
    assert "Table:" in t_chunk.metadata.section
    assert t_chunk.metadata.document_type == "technical_datasheet"
    assert t_chunk.metadata.department == "engineering"
    assert t_chunk.metadata.language == "tr"
    assert len(t_chunk.metadata.chunk_id) > 10  # valid UUID

    # Verify table markdown content is preserved intact
    assert "| Steam Capacity | 5000 kg/h |" in t_chunk.content
    assert "| Design Pressure | 16 bar |" in t_chunk.content


def test_chunker_handles_empty_or_small_pages():
    chunker = TableAwareChunker()
    empty_page = ParsedPage(page_number=1, text_content="", tables=[])
    parsed_doc = ParsedDocument(
        filename="empty.txt",
        total_pages=1,
        full_markdown="",
        pages=[empty_page],
        tables=[],
    )

    chunks = chunker.chunk_document(
        parsed_doc=parsed_doc,
        document_id="doc_empty",
    )
    assert len(chunks) == 0
