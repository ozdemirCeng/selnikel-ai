import os
import tempfile
import pytest
from app.domain.parser import ParsedBlockType, ParsedDocument
from app.services.ingestion.parser import (
    DoclingParser,
    DocumentParserFactory,
    FastFallbackParser,
)


@pytest.fixture
def sample_text_file():
    content = """# Selnikel SB-100 Industrial Boiler
## Technical Specifications

The SB-100 is a high-efficiency three-pass steam boiler designed for heavy industrial operations.

| Model | Capacity (kW) | Steam Output (kg/h) | Max Pressure (bar) |
| :--- | :--- | :--- | :--- |
| SB-100 | 700 | 1000 | 16 |
| SB-200 | 1400 | 2000 | 16 |

### Maintenance Guidelines
Inspect nozzle and safety relief valves every 500 operating hours.
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def sample_pdf_file():
    from pypdf import PdfWriter

    writer = PdfWriter()
    # Create 2 blank pages with text
    page1 = writer.add_blank_page(width=595, height=842)
    page2 = writer.add_blank_page(width=595, height=842)

    with tempfile.NamedTemporaryFile(mode="wb", suffix=".pdf", delete=False) as f:
        temp_path = f.name
        writer.write(f)

    yield temp_path

    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.mark.asyncio
async def test_fallback_parser_text_with_tables(sample_text_file):
    parser = FastFallbackParser()
    assert parser.supports(sample_text_file) is True

    parsed_doc = await parser.parse(sample_text_file)
    assert isinstance(parsed_doc, ParsedDocument)
    assert parsed_doc.total_pages == 1
    assert len(parsed_doc.tables) == 1
    assert parsed_doc.tables[0].num_rows == 2
    assert "SB-100" in parsed_doc.tables[0].markdown_table
    assert len(parsed_doc.pages) == 1
    assert "Technical Specifications" in parsed_doc.pages[0].text_content


@pytest.mark.asyncio
async def test_fallback_parser_pdf(sample_pdf_file):
    parser = FastFallbackParser()
    assert parser.supports(sample_pdf_file) is True

    parsed_doc = await parser.parse(sample_pdf_file)
    assert isinstance(parsed_doc, ParsedDocument)
    assert parsed_doc.total_pages == 2
    assert len(parsed_doc.pages) == 2


@pytest.mark.asyncio
async def test_parser_factory_resolution(sample_text_file, sample_pdf_file):
    factory = DocumentParserFactory

    text_parser = factory.get_parser(sample_text_file)
    assert text_parser is not None

    pdf_parser = factory.get_parser(sample_pdf_file)
    assert pdf_parser is not None


@pytest.mark.asyncio
async def test_parser_file_not_found():
    parser = FastFallbackParser()
    with pytest.raises(FileNotFoundError):
        await parser.parse("non_existent_file_12345.pdf")
