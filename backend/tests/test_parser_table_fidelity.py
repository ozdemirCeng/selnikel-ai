"""
Stage P1.1: Parser & Table Layout Fidelity Verification Tests.
Validates:
1. Real industrial fixture manifest integrity & SHA-256 validation.
2. PDF multi-page extraction and exact parameter preservation.
3. DOCX structured extraction with GFM table conversion.
4. TableAwareChunker row integrity: tables are never split mid-row and repeat header context on multi-part splits.
5. Strict document provenance and hierarchical section breadcrumbs.
6. OCR metadata recording (ocr_applied).
7. Parser factory fallback routing and parser performance.
"""
import hashlib
import json
import pytest
from pathlib import Path
from app.domain.parser import ParsedDocument, ParsedPage, ParsedTable
from app.services.ingestion.parser import FastFallbackParser, DoclingParser, DocumentParserFactory
from app.services.ingestion.chunker import TableAwareChunker


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def manifest(fixtures_dir: Path) -> dict:
    manifest_path = fixtures_dir / "fixture_manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_fixture_manifest_and_sha256_integrity(fixtures_dir: Path, manifest: dict):
    """Verify that all physical fixtures exist on disk and match manifest SHA-256 bit-for-bit."""
    assert manifest["manifest_version"] == "1.0.0"
    assert len(manifest["fixtures"]) == 3

    for fix in manifest["fixtures"]:
        file_path = fixtures_dir / "documents" / fix["filename"]
        assert file_path.exists(), f"Missing fixture file: {file_path}"

        with open(file_path, "rb") as f:
            actual_sha = hashlib.sha256(f.read()).hexdigest()

        assert actual_sha.lower() == fix["sha256"].lower(), f"SHA-256 mismatch on {fix['filename']}"
        assert fix["ocr_applied"] is False


@pytest.mark.asyncio
async def test_docx_parser_table_fidelity(fixtures_dir: Path):
    """Verify DOCX parsing with python-docx and exact Markdown table extraction."""
    docx_file = fixtures_dir / "documents" / "Monoblock_Burner_Maintenance_Manual.docx"
    parser = FastFallbackParser()

    assert parser.supports(str(docx_file)) is True
    parsed_doc = await parser.parse(str(docx_file))

    assert parsed_doc.filename == "Monoblock_Burner_Maintenance_Manual.docx"
    assert parsed_doc.metadata["ocr_applied"] is False
    assert parsed_doc.metadata["parser_name"] == "fast_fallback_docx"
    assert len(parsed_doc.tables) == 1

    table = parsed_doc.tables[0]
    assert table.num_cols == 4
    assert table.num_rows == 5
    assert "Burner Nozzles" in table.markdown_table
    assert "500 hour" in table.markdown_table
    assert "25 Nm" in table.markdown_table
    assert "6 month" in table.markdown_table
    assert "1 year" in table.markdown_table


@pytest.mark.asyncio
async def test_pdf_multipage_parser_fidelity(fixtures_dir: Path):
    """Verify PDF multi-page extraction with page attribution and section headers."""
    pdf_file = fixtures_dir / "documents" / "SB_Series_Steam_Boiler_Datasheet.pdf"
    parser = FastFallbackParser()

    assert parser.supports(str(pdf_file)) is True
    parsed_doc = await parser.parse(str(pdf_file))

    assert parsed_doc.filename == "SB_Series_Steam_Boiler_Datasheet.pdf"
    assert parsed_doc.total_pages == 3
    assert len(parsed_doc.pages) == 3
    assert parsed_doc.metadata["ocr_applied"] is False

    # Page 1: General specs
    p1 = parsed_doc.pages[0]
    assert p1.page_number == 1
    assert "12953" in p1.text_content
    assert "ASME Section I" in p1.text_content

    # Page 2: Operating parameters
    p2 = parsed_doc.pages[1]
    assert p2.page_number == 2
    assert "SB-500" in p2.text_content
    assert "16.0 bar" in p2.text_content
    assert "3500 kW" in p2.text_content

    # Page 3: Safety valves
    p3 = parsed_doc.pages[2]
    assert p3.page_number == 3
    assert "16.5 bar" in p3.text_content
    assert "1250 kg/h" in p3.text_content


def test_table_aware_chunker_row_integrity_and_header_repetition():
    """
    CRITICAL INVARIANT TEST:
    Verify that large tables are NEVER split mid-row and repeat header rows across chunk slices.
    """
    table_md = """| Model | Capacity | Pressure | Temp |
| :--- | :--- | :--- | :--- |
| SB-100 | 100 kg/h | 8.0 bar | 175 °C |
| SB-200 | 200 kg/h | 10.0 bar | 184 °C |
| SB-500 | 500 kg/h | 12.0 bar | 191 °C |
| SB-1000 | 1000 kg/h | 16.0 bar | 204 °C |
| SB-2000 | 2000 kg/h | 20.0 bar | 214 °C |
| SB-5000 | 5000 kg/h | 25.0 bar | 225 °C |"""

    parsed_table = ParsedTable(
        table_id="tab-01",
        page_number=2,
        markdown_table=table_md,
        num_rows=6,
        num_cols=4,
        headers=["Model", "Capacity", "Pressure", "Temp"],
        caption="Boiler Models",
    )

    doc = ParsedDocument(
        filename="test_boiler.pdf",
        total_pages=1,
        full_markdown=table_md,
        pages=[ParsedPage(page_number=2, text_content="", tables=[parsed_table], section_headers=["2. Technical Specs"])],
        tables=[parsed_table],
        blocks=[],
        metadata={},
    )

    # Use very small max_chunk_chars to force multi-chunk splitting
    chunker = TableAwareChunker(max_chunk_chars=220)
    chunks = chunker.chunk_document(doc, document_id="doc-boiler-01", document_version=2)

    assert len(chunks) > 1, "Table should be split into multiple chunk slices."

    for chunk in chunks:
        lines = [l.strip() for l in chunk.content.splitlines() if l.strip()]
        # Verify header presence in EVERY chunk slice
        assert any("| Model | Capacity | Pressure | Temp |" in l for l in lines), "Header row missing in chunk slice"
        assert any("| :--- | :--- | :--- | :--- |" in l for l in lines), "Separator row missing in chunk slice"

        # Verify no line is a half-cut pipe
        for line in lines:
            if line.startswith("|"):
                assert line.endswith("|"), f"Table row was split mid-row: {line}"

        # Verify strict metadata provenance
        assert chunk.metadata.document_id == "doc-boiler-01"
        assert chunk.metadata.document_version == 2
        assert chunk.metadata.filename == "test_boiler.pdf"
        assert chunk.metadata.page_number == 2
        assert "2. Technical Specs" in chunk.metadata.section


@pytest.mark.asyncio
async def test_parser_factory_fallback_resolution(fixtures_dir: Path):
    """Verify that DocumentParserFactory resolves appropriately and produces valid ParsedDocument."""
    txt_file = fixtures_dir / "documents" / "Thermal_Oil_Heater_Operating_Limits.txt"
    parser = DocumentParserFactory.get_parser(str(txt_file), force_fallback=True)

    assert isinstance(parser, FastFallbackParser)
    parsed = await parser.parse(str(txt_file))

    assert parsed.filename == "Thermal_Oil_Heater_Operating_Limits.txt"
    assert len(parsed.tables) == 1
    assert "Thermal Oil Operational Limits" in parsed.full_markdown
    assert "320 °C" in parsed.full_markdown
    assert "25 m³/h" in parsed.full_markdown
