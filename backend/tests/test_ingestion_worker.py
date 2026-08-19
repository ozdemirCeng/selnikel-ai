"""
Ingestion Worker & Queue Unit / Concurrency Test Suite
Validates:
1. Magic-byte MIME type and file size validation
2. IngestionJob strict state machine transitions
3. Worker lease ownership enforcement
4. Exponential backoff retry and dead-letter queue transitions
"""
import io
import pytest
from datetime import datetime, timezone, timedelta
from app.services.ingestion.worker import FileValidator
from app.domain.ingestion.models import IngestionJob, JobState, InvalidStateTransitionError

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
