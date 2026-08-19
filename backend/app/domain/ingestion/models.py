"""
Domain Models for Asynchronous Ingestion Job State Machine.
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field

class JobState(str, Enum):
    QUEUED = "queued"
    VALIDATING = "validating"
    PARSING = "parsing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class IngestionJob(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str = Field(default_factory=lambda: str(uuid4()))
    document_id: str
    revision_id: str
    state: JobState = JobState.QUEUED
    progress: float = 0.0  # 0.0 to 100.0
    attempt: int = 1
    max_attempts: int = 3
    worker_lease_id: Optional[str] = None
    lease_expires_at: Optional[datetime] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def is_active(self) -> bool:
        return self.state in [
            JobState.QUEUED,
            JobState.VALIDATING,
            JobState.PARSING,
            JobState.CHUNKING,
            JobState.EMBEDDING,
            JobState.INDEXING,
            JobState.VERIFYING
        ]
