import hashlib
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.domain.parser import ParsedDocument, ParsedPage
from app.services.ingestion.pipeline import IngestionPipeline


@pytest.mark.asyncio
async def test_sha256_deduplication_detection():
    # Setup mock storage, parser, and chunker
    mock_storage = MagicMock()
    content_bytes = b"# Test Document Content For Selnikel Boiler"
    expected_hash = hashlib.sha256(content_bytes).hexdigest()
    mock_storage.compute_sha256.return_value = expected_hash
    mock_storage.save_file = AsyncMock(return_value=(expected_hash, "/fake/path.md", len(content_bytes)))

    # Mock Session with existing doc
    mock_session = AsyncMock()
    mock_existing_doc = MagicMock()
    mock_existing_doc.id = "existing_doc_id"
    mock_existing_doc.file_hash = expected_hash
    mock_existing_doc.version = 1

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_existing_doc
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    pipeline = IngestionPipeline(storage=mock_storage)

    doc, chunks, is_dup = await pipeline.ingest_document(
        session=mock_session,
        filename="test.md",
        content=content_bytes,
        allow_duplicate=False,
    )

    assert is_dup is True
    assert doc.id == "existing_doc_id"
    assert len(chunks) == 0


@pytest.mark.asyncio
async def test_ingest_new_document_workflow():
    content_bytes = b"# New Industrial Boiler Specification\n\nOperating pressure is 16 bar."
    file_hash = hashlib.sha256(content_bytes).hexdigest()

    mock_storage = MagicMock()
    mock_storage.compute_sha256.return_value = file_hash
    mock_storage.save_file = AsyncMock(return_value=(file_hash, "/fake/path.md", len(content_bytes)))

    mock_parser = AsyncMock()
    mock_parsed_doc = ParsedDocument(
        filename="new_spec.md",
        total_pages=1,
        full_markdown=content_bytes.decode(),
        pages=[ParsedPage(page_number=1, text_content=content_bytes.decode(), tables=[])],
    )
    mock_parser.parse.return_value = mock_parsed_doc

    mock_parser_factory = MagicMock()
    mock_parser_factory.get_parser.return_value = mock_parser

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None  # No existing doc
    mock_session.execute.return_value = mock_result

    pipeline = IngestionPipeline(
        storage=mock_storage,
        parser_factory=mock_parser_factory,
    )

    doc, chunks, is_dup = await pipeline.ingest_document(
        session=mock_session,
        filename="new_spec.md",
        content=content_bytes,
        department="engineering",
        document_type="technical_specification",
        language="tr",
    )

    assert is_dup is False
    assert doc.status == "indexed"
    assert doc.file_hash == file_hash
    assert len(chunks) >= 1
    assert chunks[0].metadata.department == "engineering"
    assert chunks[0].metadata.language == "tr"
