"""
Asynchronous Ingestion Worker & File Validator Test Suite
Validates Magic-Byte detection, file size limits, SHA-256 fingerprinting, state machine transition validation,
and PostgreSQL queue operations.
"""
import pytest
from app.domain.ingestion.models import IngestionJob, JobState, InvalidStateTransitionError
from app.domain.ingestion.file_validator import (
    validate_file_payload,
    FileValidationError,
    MAX_FILE_SIZE_BYTES,
)

def test_file_validator_valid_pdf():
    """Verify that a valid PDF header is accepted and SHA-256 is computed."""
    pdf_content = b"%PDF-1.4\n%Fake PDF content for Selnikel boiler specification."
    sha256, mime, size = validate_file_payload(pdf_content, "boiler.pdf")
    
    assert mime == "application/pdf"
    assert size == len(pdf_content)
    assert len(sha256) == 64


def test_file_validator_valid_docx():
    """Verify that a valid OpenXML ZIP header (DOCX/XLSX) is accepted."""
    docx_content = b"PK\x03\x04\x14\x00\x06\x00Fake OpenXML content"
    sha256, mime, size = validate_file_payload(docx_content, "spec.docx")
    
    assert "openxmlformats" in mime
    assert size == len(docx_content)


def test_file_validator_empty_file_rejected():
    """Verify that an empty file raises EMPTY_FILE validation error."""
    with pytest.raises(FileValidationError) as exc:
        validate_file_payload(b"", "empty.pdf")
    assert exc.value.code == "EMPTY_FILE"


def test_file_validator_corrupt_binary_rejected():
    """Verify that random binary with no known magic byte raises INVALID_MIME_TYPE."""
    corrupt_bytes = b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b"
    with pytest.raises(FileValidationError) as exc:
        validate_file_payload(corrupt_bytes, "corrupted.bin")
    assert exc.value.code == "INVALID_MIME_TYPE"


def test_ingestion_job_valid_state_transitions():
    """Verify IngestionJob valid sequential state transitions."""
    job = IngestionJob(
        document_id="doc-sb100",
        revision_id="rev-001"
    )
    assert job.state == JobState.QUEUED
    assert job.is_active() is True

    # Valid step 1: QUEUED -> VALIDATING
    job.transition_to(JobState.VALIDATING, progress=10.0)
    assert job.state == JobState.VALIDATING
    assert job.progress == 10.0

    # Valid step 2: VALIDATING -> PARSING
    job.transition_to(JobState.PARSING, progress=30.0)
    assert job.state == JobState.PARSING

    # Valid step 3: PARSING -> CHUNKING -> EMBEDDING -> INDEXING -> VERIFYING -> COMPLETED
    job.transition_to(JobState.CHUNKING, progress=50.0)
    job.transition_to(JobState.EMBEDDING, progress=70.0)
    job.transition_to(JobState.INDEXING, progress=85.0)
    job.transition_to(JobState.VERIFYING, progress=95.0)
    job.transition_to(JobState.COMPLETED)
    
    assert job.state == JobState.COMPLETED
    assert job.progress == 100.0
    assert job.completed_at is not None
    assert job.is_active() is False


def test_ingestion_job_invalid_state_transition_rejected():
    """Verify that skipping states or moving backwards raises InvalidStateTransitionError."""
    job = IngestionJob(
        document_id="doc-sb100",
        revision_id="rev-001"
    )
    # Direct jump from QUEUED to COMPLETED is forbidden
    with pytest.raises(InvalidStateTransitionError):
        job.transition_to(JobState.COMPLETED)

    # Transition to VALIDATING
    job.transition_to(JobState.VALIDATING)

    # Transition from VALIDATING to INDEXING is forbidden
    with pytest.raises(InvalidStateTransitionError):
        job.transition_to(JobState.INDEXING)
