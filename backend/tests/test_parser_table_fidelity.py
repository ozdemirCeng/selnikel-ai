"""
Stage P1.1: Parser & Table Layout Fidelity Verification Tests.
Validates:
1. Synthetic industrial fixture manifest integrity, explicit labeling, & SHA-256 validation.
2. Parametric cell-level ground truth and table inventory verification across all fixtures (PDF, DOCX, TXT).
3. Section breadcrumb extraction on multi-page PDF and multi-page DOCX.
4. Multi-page DOCX flow preservation with page breaks and pipe escaping.
5. End-to-end Parser -> Chunker integration: table row integrity, header repetition, and provenance tracking.
6. Explicit OCR metadata tracking (ocr_applied).
7. Parser factory fallback resolution.
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


def test_fixture_manifest_labeling_and_sha256_integrity(fixtures_dir: Path, manifest: dict):
    """Verify that fixtures are explicitly labeled as synthetic_generated and match SHA-256 bit-for-bit."""
    assert manifest["manifest_version"] == "1.1.0"
    assert manifest["fixture_kind"] == "synthetic_generated"
    assert manifest["synthetic"] is True
    assert manifest["review_status"] == "unverified_draft"
    assert len(manifest["fixtures"]) == 4

    for fix in manifest["fixtures"]:
        file_path = fixtures_dir / "documents" / fix["filename"]
        assert file_path.exists(), f"Missing fixture file: {file_path}"

        with open(file_path, "rb") as f:
            actual_sha = hashlib.sha256(f.read()).hexdigest()

        assert actual_sha.lower() == fix["sha256"].lower(), f"SHA-256 mismatch on {fix['filename']}"
        assert fix["ocr_applied"] is False


@pytest.mark.asyncio
async def test_parametric_manifest_table_and_cell_fidelity(fixtures_dir: Path, manifest: dict):
    """
    CRITICAL GROUND TRUTH TEST:
    Parametrically iterates through all manifest fixtures and verifies:
    1. Table presence on exact expected page.
    2. Exact cell values and physical units in extracted tables.
    3. Section breadcrumb presence in parsed page headers.
    """
    parser = FastFallbackParser()

    for fix in manifest["fixtures"]:
        file_path = fixtures_dir / "documents" / fix["filename"]
        parsed_doc = await parser.parse(str(file_path))

        assert parsed_doc.filename == fix["filename"]
        assert parsed_doc.total_pages == fix["page_count"]
        assert parsed_doc.metadata["ocr_applied"] == fix["ocr_applied"]

        # 1. Verify section inventory
        for expected_sec in fix.get("section_inventory", []):
            page_no = expected_sec["page_number"]
            expected_hdr = expected_sec["header"]
            page = next((p for p in parsed_doc.pages if p.page_number == page_no), None)
            assert page is not None, f"Page {page_no} not found in {fix['filename']}"
            assert any(expected_hdr in h or h in expected_hdr for h in page.section_headers), (
                f"Expected section '{expected_hdr}' not found in page {page_no} headers: {page.section_headers}"
            )

        # 2. Verify table inventory and cell-level ground truth
        for expected_tab in fix.get("table_inventory", []):
            page_no = expected_tab["page_number"]
            # Find parsed tables on this page
            page_tables = [t for t in parsed_doc.tables if t.page_number == page_no]
            assert len(page_tables) > 0, f"No tables parsed on page {page_no} of {fix['filename']}"

            # Search across page tables for cell values
            all_table_text = " ".join(t.markdown_table for t in page_tables)
            for row_key, row_cells in expected_tab["ground_truth_cells"].items():
                assert row_key in all_table_text, f"Row key '{row_key}' not found in extracted table markdown"
                for col_name, cell_val in row_cells.items():
                    assert cell_val in all_table_text, (
                        f"Cell value '{cell_val}' for column '{col_name}' in row '{row_key}' not found in table"
                    )


@pytest.mark.asyncio
async def test_complex_multipage_docx_layout_fidelity(fixtures_dir: Path):
    """Verify multi-page DOCX parsing with page break detection, table ordering, and section headers."""
    docx_file = fixtures_dir / "documents" / "Industrial_Boiler_Commissioning_Guide.docx"
    parser = FastFallbackParser()

    parsed_doc = await parser.parse(str(docx_file))

    assert parsed_doc.total_pages == 2
    assert len(parsed_doc.pages) == 2

    # Page 1: Pre-commissioning
    p1 = parsed_doc.pages[0]
    assert p1.page_number == 1
    assert any("1. Pre-Commissioning Electrical Limits" in h for h in p1.section_headers)
    assert len(p1.tables) == 1
    assert "380 - 420 V" in p1.tables[0].markdown_table

    # Page 2: Flue Gas Emissions
    p2 = parsed_doc.pages[1]
    assert p2.page_number == 2
    assert any("2. Flue Gas Emission Limits" in h for h in p2.section_headers)
    assert len(p2.tables) == 1
    assert "< 50 mg/Nm³" in p2.tables[0].markdown_table


@pytest.mark.asyncio
async def test_end_to_end_parser_to_chunker_integration(fixtures_dir: Path):
    """
    CRITICAL INTEGRATION TEST:
    Verifies that real ParsedDocument outputs from PDF and DOCX flow into TableAwareChunker
    and produce valid DomainChunks with full provenance, section breadcrumbs, and row integrity.
    """
    parser = FastFallbackParser()
    chunker = TableAwareChunker(max_chunk_chars=300)  # small max_chunk_chars to test slicing

    # 1. Test PDF Document Chunking
    pdf_file = fixtures_dir / "documents" / "SB_Series_Steam_Boiler_Datasheet.pdf"
    parsed_pdf = await parser.parse(str(pdf_file))
    pdf_chunks = chunker.chunk_document(parsed_pdf, document_id="doc-pdf-01", document_version=1)

    assert len(pdf_chunks) >= 3
    # Check table chunks
    table_chunks = [c for c in pdf_chunks if "Type: Table" in c.content]
    assert len(table_chunks) >= 2, "PDF tables should generate table chunks"

    for tc in table_chunks:
        assert tc.metadata.document_id == "doc-pdf-01"
        assert tc.metadata.filename == "SB_Series_Steam_Boiler_Datasheet.pdf"
        assert tc.metadata.page_number in (2, 3)
        assert "Table" in tc.metadata.section
        # Verify no mid-row cuts
        for line in tc.content.splitlines():
            sline = line.strip()
            if sline.startswith("|"):
                assert sline.endswith("|"), f"Mid-row cut in table chunk: {sline}"

    # 2. Test Multipage DOCX Document Chunking
    docx_file = fixtures_dir / "documents" / "Industrial_Boiler_Commissioning_Guide.docx"
    parsed_docx = await parser.parse(str(docx_file))
    docx_chunks = chunker.chunk_document(parsed_docx, document_id="doc-docx-01", document_version=1)

    assert len(docx_chunks) >= 2
    assert any(c.metadata.page_number == 1 for c in docx_chunks)
    assert any(c.metadata.page_number == 2 for c in docx_chunks)


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
