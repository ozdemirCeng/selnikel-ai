"""
Domain Models for Asynchronous Ingestion Job State Machine.
Enforces strict lifecycle state transition rules.
"""
from datetime import datetime, timezone
from typing import Optional, Set
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

# Permitted state transitions map
PERMITTED_TRANSITIONS = {
    JobState.QUEUED: {JobState.VALIDATING, JobState.CANCELLED, JobState.FAILED},
    JobState.VALIDATING: {JobState.PARSING, JobState.FAILED, JobState.CANCELLED},
    JobState.PARSING: {JobState.CHUNKING, JobState.FAILED, JobState.CANCELLED},
    JobState.CHUNKING: {JobState.EMBEDDING, JobState.FAILED, JobState.CANCELLED},
    JobState.EMBEDDING: {JobState.INDEXING, JobState.FAILED, JobState.CANCELLED},
    JobState.INDEXING: {JobState.VERIFYING, JobState.FAILED, JobState.CANCELLED},
    JobState.VERIFYING: {JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED},
    JobState.COMPLETED: set(),  # Terminal state
    JobState.CANCELLED: set(),  # Terminal state
    JobState.FAILED: {JobState.QUEUED},  # Can be re-queued on retry
}

class InvalidStateTransitionError(Exception):
    def __init__(self, current_state: JobState, target_state: JobState):
        self.current_state = current_state
        self.target_state = target_state
        super().__init__(
            f"Geçersiz durum geçişi: '{current_state.value}' durumundan '{target_state.value}' durumuna geçilemez."
        )


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
    next_attempt_at: Optional[datetime] = None
    dead_letter: bool = False
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def transition_to(self, new_state: JobState, progress: Optional[float] = None) -> None:
        """Transitions job to a new state enforcing valid transition graph."""
        if new_state != self.state:
            allowed = PERMITTED_TRANSITIONS.get(self.state, set())
            if new_state not in allowed:
                raise InvalidStateTransitionError(self.state, new_state)
            self.state = new_state

        if progress is not None:
            self.progress = max(0.0, min(100.0, progress))

        if new_state == JobState.COMPLETED:
            self.progress = 100.0
            self.completed_at = datetime.now(timezone.utc)

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
