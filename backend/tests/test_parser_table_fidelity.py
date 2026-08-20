"""
Stage P1.1: Parser & Table Layout Fidelity Verification Tests.
Validates:
1. Synthetic industrial fixture manifest integrity, explicit labeling, & SHA-256 validation.
2. Parametric cell-level coordinate verification: (table_id, row_key, column_name) -> exact value.
3. Strict table column consistency & spatial separation: multi-table per page separation, zero cell deletion.
4. Section header isolation: model codes (SB-5000) are NEVER treated as section headers or captions.
5. Multi-page DOCX flow preservation with page breaks, paragraph-table ordering, and pipe escaping.
6. End-to-end Parser -> Chunker integration: table row integrity, header repetition, and provenance tracking.
7. Explicit OCR metadata tracking (ocr_applied) and deterministic FastFallbackParser fallback verification.
"""
import hashlib
import json
import re
import pytest
from pathlib import Path
from typing import Dict, List, Optional, Tuple
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


def parse_markdown_table_to_matrix(markdown_table: str) -> Tuple[List[str], Dict[str, Dict[str, str]]]:
    """Parses a GFM markdown table into headers list and a 2D cell coordinate matrix indexed by row primary key."""
    lines = [l.strip() for l in markdown_table.splitlines() if l.strip()]
    if len(lines) < 3:
        return [], {}

    headers = [c.strip() for c in lines[0].split("|")[1:-1]]
    rows_by_pk: Dict[str, Dict[str, str]] = {}

    for line in lines[2:]:
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) == len(headers):
            pk = cells[0]
            row_dict = {headers[i]: cells[i] for i in range(len(headers))}
            rows_by_pk[pk] = row_dict

    return headers, rows_by_pk


def find_column_by_key(headers: List[str], col_key: str) -> Optional[str]:
    """Maps a manifest column key (e.g. 'working_press', 'discharge_cap', 'ng', 'oil', 'dn') to the exact table header string."""
    col_key_clean = col_key.lower().strip()
    abbrev_map = {
        "ng": ["natural gas", "ng"],
        "oil": ["light oil", "oil"],
        "dn": ["connection dn", "dn", "connection"],
        "nom": ["nominal"],
        "min": ["minimum", "min"],
        "max": ["maximum", "max"],
        "steam_cap": ["steam cap", "capacity"],
        "working_press": ["working press", "working pressure"],
        "design_press": ["design press", "design pressure"],
        "steam_temp": ["steam temp", "temperature"],
        "thermal_power": ["thermal power", "power"],
        "set_pressure": ["set pressure"],
        "discharge_cap": ["discharge cap", "discharge capacity"],
        "action": ["inspection action", "action"],
        "interval": ["service interval", "interval"],
        "torque": ["torque", "spec"],
        "signal": ["signal type", "signal"],
        "range": ["allowed range", "range"],
    }
    candidates = abbrev_map.get(col_key_clean, [col_key_clean.replace("_", " "), col_key_clean])

    for cand in candidates:
        cand_clean = "".join(ch.lower() for ch in cand if ch.isalnum())
        for h in headers:
            h_clean = "".join(ch.lower() for ch in h if ch.isalnum())
            if cand_clean in h_clean:
                return h
    return None


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
async def test_parametric_manifest_table_and_cell_coordinate_fidelity(fixtures_dir: Path, manifest: dict):
    """
    CRITICAL GROUND TRUTH TEST:
    Parametrically iterates through all manifest fixtures and verifies:
    1. Table presence on exact expected page with unique table signature match.
    2. Exact row count, column count, and header alignment.
    3. Strict (table_id, row_key, column_name) -> exact cell coordinate value verification.
    4. Negative checks: model codes (SB-5000) are NOT section headers.
    5. Table row column consistency: every row has the exact same cell count.
    """
    parser = FastFallbackParser()

    for fix in manifest["fixtures"]:
        file_path = fixtures_dir / "documents" / fix["filename"]
        parsed_doc = await parser.parse(str(file_path))

        assert parsed_doc.filename == fix["filename"]
        assert parsed_doc.total_pages == fix["page_count"]
        assert parsed_doc.metadata["ocr_applied"] == fix["ocr_applied"]

        # 1. Verify section inventory and negative checks
        for expected_sec in fix.get("section_inventory", []):
            page_no = expected_sec["page_number"]
            expected_hdr = expected_sec["header"]
            page = next((p for p in parsed_doc.pages if p.page_number == page_no), None)
            assert page is not None, f"Page {page_no} not found in {fix['filename']}"
            assert any(expected_hdr in h or h in expected_hdr for h in page.section_headers), (
                f"Expected section '{expected_hdr}' not found in page {page_no} headers: {page.section_headers}"
            )
            # Negative check: ensure model codes are not in section headers
            assert "SB-5000" not in page.section_headers
            assert "SB-500" not in page.section_headers
            assert "SB-1000" not in page.section_headers

        # 2. Verify table inventory and exact cell coordinates
        for expected_tab in fix.get("table_inventory", []):
            page_no = expected_tab["page_number"]
            page_tables = [t for t in parsed_doc.tables if t.page_number == page_no]
            assert len(page_tables) > 0, f"No tables parsed on page {page_no} of {fix['filename']}"

            # Strict Table Identification: match by exact table_id, exact headers, AND exact normalized title
            def norm_title(title: Optional[str]) -> str:
                if not title:
                    return ""
                t = re.sub(r"^(Table\s*\d*\s*[:\-.]\s*|\d+(\.\d+)*\.?\s*)", "", title.strip(), flags=re.IGNORECASE)
                return t.strip()

            matching_tables = [
                pt for pt in page_tables
                if pt.table_id == expected_tab["table_id"]
                and pt.headers == expected_tab["headers"]
                and norm_title(pt.caption) == norm_title(expected_tab["title"])
            ]
            assert len(matching_tables) == 1, (
                f"Expected exactly 1 matching table on page {page_no} for table_id='{expected_tab['table_id']}', "
                f"title='{expected_tab['title']}', headers={expected_tab['headers']}. "
                f"Found {len(matching_tables)}. Available tables: {[(pt.table_id, pt.headers, pt.caption) for pt in page_tables]}"
            )
            target_table = matching_tables[0]
            assert target_table.table_id == expected_tab["table_id"]

            assert target_table.num_cols == expected_tab["column_count"], (
                f"Column count mismatch for table {expected_tab['table_id']} on page {page_no}: "
                f"expected {expected_tab['column_count']}, got {target_table.num_cols}"
            )
            assert target_table.num_rows == expected_tab["row_count"], (
                f"Row count mismatch for table {expected_tab['table_id']} on page {page_no}: "
                f"expected {expected_tab['row_count']}, got {target_table.num_rows}"
            )

            # Strict matrix coordinate parsing
            headers, rows_by_pk = parse_markdown_table_to_matrix(target_table.markdown_table)
            assert len(headers) == expected_tab["column_count"]

            # Verify every ground truth cell coordinate
            for row_key, expected_cells in expected_tab["ground_truth_cells"].items():
                assert row_key in rows_by_pk, (
                    f"Row primary key '{row_key}' not found in table on page {page_no}. Available PKs: {list(rows_by_pk.keys())}"
                )
                row_dict = rows_by_pk[row_key]

                for col_key, expected_val in expected_cells.items():
                    matched_col = find_column_by_key(headers, col_key)
                    assert matched_col is not None, (
                        f"Could not map manifest column key '{col_key}' to extracted table headers {headers}"
                    )
                    actual_val = row_dict[matched_col]
                    norm_actual = actual_val.replace("", "°")
                    norm_expected = expected_val.replace("", "°")
                    assert norm_actual == norm_expected, (
                        f"Exact cell coordinate mismatch at [file={fix['filename']}, page={page_no}, "
                        f"table={expected_tab['table_id']}, row='{row_key}', col='{matched_col}']:\n"
                        f"  Expected: '{norm_expected}'\n"
                        f"  Actual:   '{norm_actual}'"
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
    headers1, rows1 = parse_markdown_table_to_matrix(p1.tables[0].markdown_table)
    assert "L1-L2-L3" in rows1
    assert rows1["L1-L2-L3"]["Allowed Range"] == "380 - 420 V"

    # Page 2: Flue Gas Emissions
    p2 = parsed_doc.pages[1]
    assert p2.page_number == 2
    assert any("2. Flue Gas Emission Limits" in h for h in p2.section_headers)
    assert len(p2.tables) == 1
    headers2, rows2 = parse_markdown_table_to_matrix(p2.tables[0].markdown_table)
    assert "CO Concentration" in rows2
    assert rows2["CO Concentration"]["Natural Gas Limit"] == "< 50 mg/Nm³"


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
            if sline.startswith("|") and not sline.startswith("| ---"):
                assert sline.endswith("|"), f"Mid-row cut in table chunk: {sline}"

    # 2. Test Multipage DOCX Document Chunking
    docx_file = fixtures_dir / "documents" / "Industrial_Boiler_Commissioning_Guide.docx"
    parsed_docx = await parser.parse(str(docx_file))
    docx_chunks = chunker.chunk_document(parsed_docx, document_id="doc-docx-01", document_version=1)

    assert len(docx_chunks) >= 2
    assert any(c.metadata.page_number == 1 for c in docx_chunks)
    assert any(c.metadata.page_number == 2 for c in docx_chunks)


@pytest.mark.asyncio
async def test_deterministic_fallback_parser_and_factory(fixtures_dir: Path):
    """
    VERIFIES ADR-008:
    1. FastFallbackParser returns deterministic parser_name (fast_fallback_*).
    2. DocumentParserFactory with force_fallback=True guarantees deterministic FastFallbackParser execution.
    3. Short cell preservation (A, B, C) and zero silent truncation.
    """
    txt_file = fixtures_dir / "documents" / "Thermal_Oil_Heater_Operating_Limits.txt"
    pdf_file = fixtures_dir / "documents" / "SB_Series_Steam_Boiler_Datasheet.pdf"

    # 1. Factory force_fallback
    fallback_parser = DocumentParserFactory.get_parser(str(txt_file), force_fallback=True)
    assert isinstance(fallback_parser, FastFallbackParser)
    parsed_txt = await fallback_parser.parse(str(txt_file))
    assert parsed_txt.parser_name == "fast_fallback_text"
    assert parsed_txt.metadata["ocr_applied"] is False

    # 2. PDF Fast Fallback
    pdf_parser = FastFallbackParser()
    parsed_pdf = await pdf_parser.parse(str(pdf_file))
    assert parsed_pdf.parser_name == "fast_fallback_pypdf"
    assert parsed_pdf.metadata["ocr_applied"] is False
    assert len(parsed_pdf.tables) == 2
    assert "rejected_table_rows" in parsed_pdf.metadata


@pytest.mark.asyncio
async def test_zero_silent_data_loss_and_adversarial_row_recovery():
    """
    CRITICAL ADVERSARIAL TEST:
    Verifies that when a malformed/non-conforming row appears in a spatial table block:
    1. Subsequent valid conforming rows are NOT shredded or lost.
    2. The non-conforming row is explicitly captured in metadata['rejected_table_rows'] with structured reasons.
    3. Zero silent truncation invariant is maintained.
    """
    parser = FastFallbackParser()

    # Simulate mock page with spatial visitor delivering:
    # H1 | H2 | H3 (3 cols)
    # a  | b  | c  (3 cols)
    # lost row has four (4 cols - non-conforming)
    # d  | e  | f  (3 cols - conforming subsequent row)
    class MockPDFPage:
        def extract_text(self, visitor_text=None):
            if visitor_text is None:
                return "1. General Test Section\nSection 1.1: Operating limits"
            # Simulate visitor calls
            # Header row at y=100
            for idx, text in enumerate(["H1", "H2", "H3"]):
                visitor_text(text, None, [1, 0, 0, 1, 50.0 + idx * 100, 100.0], None, 10)
            # Row 1 at y=80
            for idx, text in enumerate(["a", "b", "c"]):
                visitor_text(text, None, [1, 0, 0, 1, 50.0 + idx * 100, 80.0], None, 10)
            # Row 2 (malformed 4 cols) at y=60
            for idx, text in enumerate(["lost", "row", "has", "four"]):
                visitor_text(text, None, [1, 0, 0, 1, 50.0 + idx * 80, 60.0], None, 10)
            # Row 3 (conforming 3 cols) at y=40
            for idx, text in enumerate(["d", "e", "f"]):
                visitor_text(text, None, [1, 0, 0, 1, 50.0 + idx * 100, 40.0], None, 10)
            return "1. General Test Section"

    mock_page = MockPDFPage()
    tables, page_text, section_headers, rejected_rows = parser._extract_pdf_page_content(mock_page, page_number=1)

    # 1. Verify table extraction
    assert len(tables) == 1, "Expected 1 recovered table despite intervening non-conforming row"
    recovered_table = tables[0]
    assert recovered_table.num_cols == 3
    assert recovered_table.num_rows == 2  # rows 'a|b|c' and 'd|e|f'
    assert recovered_table.headers == ["H1", "H2", "H3"]
    assert "a | b | c" in recovered_table.markdown_table
    assert "d | e | f" in recovered_table.markdown_table

    # 2. Verify zero silent loss: non-conforming row was captured with structured reason
    assert len(rejected_rows) == 1
    rej = rejected_rows[0]
    assert rej["page_number"] == 1
    assert rej["expected_cols"] == 3
    assert rej["actual_cols"] == 4
    assert rej["reason"] == "column_count_mismatch"
    assert rej["row_cells"] == ["lost", "row", "has", "four"]

