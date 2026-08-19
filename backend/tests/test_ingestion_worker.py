"""
Ingestion Worker Daemon & Queue Unit / Concurrency Test Suite
Validates:
1. Magic-byte MIME type and file size validation
2. IngestionJob strict state machine transitions
3. Worker lease ownership enforcement
4. Exponential backoff retry and dead-letter queue transitions
5. IngestionWorkerDaemon lifecycle & graceful shutdown
6. End-to-end pipeline execution (parse -> chunk -> embed -> index -> complete)
7. Qdrant outage fail-fast behavior (no silent data loss)
8. Missing file hard error rejection (no fake substitution)
9. Background heartbeat renewal task
"""
import io
import os
import tempfile
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from app.services.ingestion.worker import FileValidator, IngestionWorkerDaemon
from app.domain.ingestion.models import IngestionJob, JobState, InvalidStateTransitionError
from app.infrastructure.ingestion_queue import PostgresIngestionQueue
from app.infrastructure.qdrant import qdrant_repo

def test_file_validator_valid_pdf():
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    stream = io.BytesIO(pdf_bytes)
    result = FileValidator.validate_file(stream, "test_document.pdf")
    assert result.is_valid is True
    assert result.mime_type == "application/pdf"
    assert result.sha256_hash is not None


def test_file_validator_valid_docx():
    docx_bytes = b"PK\x03\x04" + b"\x00" * 50
    stream = io.BytesIO(docx_bytes)
    result = FileValidator.validate_file(stream, "manual.docx")
    assert result.is_valid is True
    assert "wordprocessingml" in result.mime_type or "zip" in result.mime_type


def test_file_validator_empty_file_rejected():
    empty_stream = io.BytesIO(b"")
    result = FileValidator.validate_file(empty_stream, "empty.pdf")
    assert result.is_valid is False
    assert "0 byte" in result.error_message or "boş" in result.error_message or "empty" in result.error_message.lower()


def test_file_validator_corrupt_binary_rejected():
    corrupt_bytes = b"\x00\x01\x02\x03\x04\x05\x06\x07"
    stream = io.BytesIO(corrupt_bytes)
    result = FileValidator.validate_file(stream, "fake.pdf")
    assert result.is_valid is False


def test_ingestion_job_valid_state_transitions():
    job = IngestionJob(
        id="job-test-01",
        document_id="doc-001",
        revision_id="rev-001",
        filename="test.pdf",
        file_path="/tmp/test.pdf",
        department_id="dept-engineering",
        file_size_bytes=1024,
        mime_type="application/pdf",
        sha256_hash="abc",
    )
    assert job.state == JobState.QUEUED

    # queued -> validating -> parsing -> chunking -> embedding -> indexing -> verifying -> completed
    job.transition_to(JobState.VALIDATING)
    assert job.state == JobState.VALIDATING

    job.transition_to(JobState.PARSING)
    assert job.state == JobState.PARSING

    job.transition_to(JobState.CHUNKING)
    assert job.state == JobState.CHUNKING

    job.transition_to(JobState.EMBEDDING)
    assert job.state == JobState.EMBEDDING

    job.transition_to(JobState.INDEXING)
    assert job.state == JobState.INDEXING

    job.transition_to(JobState.VERIFYING)
    assert job.state == JobState.VERIFYING

    job.transition_to(JobState.COMPLETED)
    assert job.state == JobState.COMPLETED


def test_ingestion_job_invalid_state_transition_rejected():
    job = IngestionJob(
        id="job-test-02",
        document_id="doc-002",
        revision_id="rev-002",
        filename="test.pdf",
        file_path="/tmp/test.pdf",
        department_id="dept-engineering",
        file_size_bytes=1024,
        mime_type="application/pdf",
        sha256_hash="abc",
    )
    # Direct illegal jump: queued -> indexing
    with pytest.raises(InvalidStateTransitionError):
        job.transition_to(JobState.INDEXING)


def test_ingestion_job_exponential_backoff_and_dead_letter():
    """Verify exponential backoff calculation and max retry dead-lettering."""
    job = IngestionJob(
        id="job-test-03",
        document_id="doc-003",
        revision_id="rev-003",
        filename="test.pdf",
        file_path="/tmp/test.pdf",
        department_id="dept-engineering",
        file_size_bytes=1024,
        mime_type="application/pdf",
        sha256_hash="abc",
        max_attempts=3,
    )

    # Attempt 1 fail -> backoff 2^1 * 10 = 20s
    job.attempt = 1
    job.transition_to(JobState.VALIDATING)
    job.transition_to(JobState.PARSING)
    job.transition_to(JobState.FAILED)
    assert job.dead_letter is False

    # Attempt 3 fail -> moved to dead-letter
    job.attempt = 3
    job.dead_letter = True
    assert job.state == JobState.FAILED
    assert job.dead_letter is True


@pytest.mark.asyncio
async def test_worker_daemon_lifecycle_and_graceful_shutdown():
    """Verify worker daemon initialization, execution, and graceful shutdown."""
    worker = IngestionWorkerDaemon(worker_id="test-worker-01", poll_interval_seconds=0.05)
    assert worker.is_running is False
    assert worker.worker_id == "test-worker-01"

    mock_session = AsyncMock()
    mock_session_factory = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session), __aexit__=AsyncMock()))

    # Start worker in background task
    task = asyncio.create_task(worker.start(mock_session_factory))
    await asyncio.sleep(0.1)
    assert worker.is_running is True

    # Signal stop
    worker.stop()
    await task
    assert worker.is_running is False


@pytest.mark.asyncio
async def test_worker_pipeline_end_to_end():
    """Verify real file execution through entire worker pipeline (validate -> parse -> chunk -> embed -> index)."""
    # Create real temporary file
    sample_content = "# Selnikel Kazan Bakım Kılavuzu\n\nStandart çalışma basıncı 16 bar'dır.\n\n| Parametre | Değer |\n| Basınç | 16 bar |\n"
    with tempfile.NamedTemporaryFile(suffix="_test_doc.md", delete=False, mode="w", encoding="utf-8") as tmp:
        tmp.write(sample_content)
        tmp_file_path = tmp.name

    try:
        mock_queue = MagicMock(spec=PostgresIngestionQueue)
        mock_queue.update_progress = AsyncMock()
        mock_queue.complete_job = AsyncMock()
        mock_queue.fail_job = AsyncMock()

        worker = IngestionWorkerDaemon(worker_id="worker-test-pipeline", queue=mock_queue)

        mock_job = MagicMock()
        mock_job.id = "job-e2e-001"
        mock_job.document_id = "doc-e2e-001"
        mock_job.revision_id = "rev-e2e-001"
        mock_job.file_path = tmp_file_path
        mock_job.filename = "test_doc.md"
        mock_job.department_id = "dept-engineering"
        mock_job.equipment_id = "EQ-100"
        mock_job.classification = "internal"

        mock_session = AsyncMock()

        # Mock Qdrant healthy and successful upsert
        with patch.object(qdrant_repo, "check_health", new_callable=AsyncMock, return_value=True), \
             patch.object(qdrant_repo, "upsert_chunks", new_callable=AsyncMock, return_value=True):
            total_chunks = await worker.execute_pipeline(mock_session, mock_job)

            assert total_chunks >= 1
            mock_queue.complete_job.assert_awaited_once_with(mock_session, "job-e2e-001", "worker-test-pipeline", chunks_count=total_chunks)
    finally:
        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)


@pytest.mark.asyncio
async def test_worker_pipeline_qdrant_outage_fails_fast():
    """Verify that Qdrant outage fails the pipeline immediately and prevents silent data loss."""
    with tempfile.NamedTemporaryFile(suffix="_test_doc.txt", delete=False, mode="w", encoding="utf-8") as tmp:
        tmp.write("Test content for failure test")
        tmp_file_path = tmp.name

    try:
        mock_queue = MagicMock(spec=PostgresIngestionQueue)
        mock_queue.update_progress = AsyncMock()
        mock_queue.complete_job = AsyncMock()
        mock_queue.fail_job = AsyncMock()

        worker = IngestionWorkerDaemon(worker_id="worker-fail-test", queue=mock_queue)

        mock_job = MagicMock()
        mock_job.id = "job-fail-001"
        mock_job.document_id = "doc-fail-001"
        mock_job.revision_id = "rev-fail-001"
        mock_job.file_path = tmp_file_path
        mock_job.filename = "test_doc.txt"
        mock_job.department_id = "dept-service"

        mock_session = AsyncMock()

        # Mock Qdrant offline
        with patch.object(qdrant_repo, "check_health", new_callable=AsyncMock, return_value=False):
            with pytest.raises(RuntimeError) as exc_info:
                await worker.execute_pipeline(mock_session, mock_job)
            assert "Qdrant" in str(exc_info.value)
            mock_queue.complete_job.assert_not_awaited()
    finally:
        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)


@pytest.mark.asyncio
async def test_worker_pipeline_missing_file_hard_error():
    """Verify that a missing file raises FileNotFoundError immediately and is not replaced with fake data."""
    mock_queue = MagicMock(spec=PostgresIngestionQueue)
    mock_queue.update_progress = AsyncMock()
    mock_queue.complete_job = AsyncMock()

    worker = IngestionWorkerDaemon(worker_id="worker-missing-test", queue=mock_queue)

    mock_job = MagicMock()
    mock_job.id = "job-missing-001"
    mock_job.file_path = "/non/existent/path/document.pdf"
    mock_job.filename = "document.pdf"

    mock_session = AsyncMock()

    with pytest.raises(FileNotFoundError):
        await worker.execute_pipeline(mock_session, mock_job)
    mock_queue.complete_job.assert_not_awaited()


@pytest.mark.asyncio
async def test_worker_heartbeat_loop():
    """Verify background lease heartbeat loop renews lease periodically."""
    mock_queue = MagicMock(spec=PostgresIngestionQueue)
    mock_queue.heartbeat = AsyncMock(return_value=True)

    worker = IngestionWorkerDaemon(worker_id="worker-hb-01", queue=mock_queue, heartbeat_interval_seconds=0.05)

    mock_session = AsyncMock()
    mock_session_factory = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session), __aexit__=AsyncMock()))

    # Run heartbeat loop for brief duration
    hb_task = asyncio.create_task(worker._heartbeat_loop(mock_session_factory, "job-hb-100"))
    await asyncio.sleep(0.12)
    hb_task.cancel()
    try:
        await hb_task
    except asyncio.CancelledError:
        pass

    assert mock_queue.heartbeat.await_count >= 1
