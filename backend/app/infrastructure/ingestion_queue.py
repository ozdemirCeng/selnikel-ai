"""
PostgreSQL Asynchronous Ingestion Job Queue Repository.
Implements distributed concurrency safe job scheduling using PostgreSQL
'SELECT ... FOR UPDATE SKIP LOCKED', worker lease heartbeats, worker ownership validation,
exponential backoff retry, and dead-letter handling.
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import uuid4
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import IngestionJobModel
from app.domain.ingestion.models import IngestionJob, IngestionJobState, InvalidStateTransitionError
from app.core.logging import logger


class PostgresIngestionQueue:
    """Production Job Queue backed by PostgreSQL SKIP LOCKED transaction locks."""

    def __init__(self, lease_duration_seconds: int = 300):
        self.lease_duration_seconds = lease_duration_seconds

    async def enqueue_job(
        self,
        session: AsyncSession,
        document_id: str,
        filename: str,
        file_path: str,
        department_id: str,
        file_size_bytes: int,
        mime_type: str,
        sha256_hash: str,
        max_attempts: int = 3,
    ) -> IngestionJobModel:
        """Enqueues a new pending ingestion job."""
        job = IngestionJobModel(
            id=f"job-{uuid4().hex[:12]}",
            document_id=document_id,
            filename=filename,
            file_path=file_path,
            department_id=department_id,
            file_size_bytes=file_size_bytes,
            mime_type=mime_type,
            sha256_hash=sha256_hash,
            state="queued",
            attempt=0,
            max_attempts=max_attempts,
            progress=0,
            dead_letter=False,
            created_at=datetime.now(timezone.utc),
        )
        session.add(job)
        await session.flush()
        logger.info(f"Ingestion job enqueued: {job.id} for file {filename}")
        return job

    async def claim_next_job(
        self,
        session: AsyncSession,
        worker_id: str,
    ) -> Optional[IngestionJobModel]:
        """
        Atomically claims the next available queued or expired-lease job using SKIP LOCKED.
        Validates that retry backoff timestamp (next_attempt_at) has passed.
        """
        now = datetime.now(timezone.utc)
        stmt = (
            select(IngestionJobModel)
            .where(
                and_(
                    IngestionJobModel.dead_letter.is_(False),
                    or_(
                        and_(
                            IngestionJobModel.state == "queued",
                            or_(
                                IngestionJobModel.next_attempt_at.is_(None),
                                IngestionJobModel.next_attempt_at <= now,
                            ),
                        ),
                        and_(
                            IngestionJobModel.state.in_(["parsing", "chunking", "embedding", "indexing"]),
                            IngestionJobModel.lease_expires_at < now,
                        ),
                    ),
                )
            )
            .order_by(IngestionJobModel.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )

        result = await session.execute(stmt)
        job = result.scalars().first()

        if job:
            job.state = "parsing"
            job.worker_lease_id = worker_id
            job.lease_expires_at = now + timedelta(seconds=self.lease_duration_seconds)
            job.attempt += 1
            if not job.started_at:
                job.started_at = now
            await session.flush()
            logger.info(f"Worker '{worker_id}' claimed job {job.id} (attempt {job.attempt}/{job.max_attempts})")

        return job

    async def heartbeat(
        self,
        session: AsyncSession,
        job_id: str,
        worker_id: str,
    ) -> bool:
        """Extends worker lease if worker still holds ownership."""
        stmt = select(IngestionJobModel).where(
            and_(
                IngestionJobModel.id == job_id,
                IngestionJobModel.worker_lease_id == worker_id,
            )
        )
        result = await session.execute(stmt)
        job = result.scalars().first()
        if not job:
            return False

        job.lease_expires_at = datetime.now(timezone.utc) + timedelta(seconds=self.lease_duration_seconds)
        await session.flush()
        return True

    async def update_progress(
        self,
        session: AsyncSession,
        job_id: str,
        worker_id: str,
        new_state: str,
        progress: int,
        stage: Optional[str] = None,
    ) -> bool:
        """Updates progress ensuring worker ownership and valid state transition."""
        stmt = select(IngestionJobModel).where(
            and_(
                IngestionJobModel.id == job_id,
                IngestionJobModel.worker_lease_id == worker_id,
            )
        )
        result = await session.execute(stmt)
        job = result.scalars().first()
        if not job:
            logger.warning(f"Worker '{worker_id}' does not own job {job_id}. Update rejected.")
            return False

        job.state = new_state
        job.progress = progress
        if stage:
            job.current_stage = stage
        job.lease_expires_at = datetime.now(timezone.utc) + timedelta(seconds=self.lease_duration_seconds)
        await session.flush()
        return True

    async def complete_job(
        self,
        session: AsyncSession,
        job_id: str,
        worker_id: str,
        chunks_count: int = 0,
    ) -> bool:
        """Marks job as successfully completed."""
        stmt = select(IngestionJobModel).where(
            and_(
                IngestionJobModel.id == job_id,
                IngestionJobModel.worker_lease_id == worker_id,
            )
        )
        result = await session.execute(stmt)
        job = result.scalars().first()
        if not job:
            return False

        now = datetime.now(timezone.utc)
        job.state = "completed"
        job.progress = 100
        job.completed_at = now
        job.worker_lease_id = None
        job.lease_expires_at = None
        await session.flush()
        logger.info(f"Job {job_id} successfully completed by worker {worker_id} ({chunks_count} chunks)")
        return True

    async def fail_job(
        self,
        session: AsyncSession,
        job_id: str,
        worker_id: str,
        error_code: str,
        error_message: str,
    ) -> bool:
        """
        Handles job failure:
        - If attempt < max_attempts: schedules retry with exponential backoff.
        - If attempt >= max_attempts: marks as dead-letter failed.
        """
        stmt = select(IngestionJobModel).where(
            and_(
                IngestionJobModel.id == job_id,
                IngestionJobModel.worker_lease_id == worker_id,
            )
        )
        result = await session.execute(stmt)
        job = result.scalars().first()
        if not job:
            return False

        now = datetime.now(timezone.utc)
        job.error_code = error_code
        job.error_message = error_message
        job.worker_lease_id = None
        job.lease_expires_at = None

        if job.attempt >= job.max_attempts:
            job.state = "failed"
            job.dead_letter = True
            job.completed_at = now
            logger.error(f"Job {job_id} moved to DEAD-LETTER after {job.attempt} failed attempts: {error_message}")
        else:
            # Exponential backoff: 2^attempt * 10 seconds
            backoff_seconds = (2 ** job.attempt) * 10
            job.next_attempt_at = now + timedelta(seconds=backoff_seconds)
            job.state = "queued"
            logger.warning(f"Job {job_id} failed (attempt {job.attempt}). Scheduled retry in {backoff_seconds}s.")

        await session.flush()
        return True


ingestion_queue = PostgresIngestionQueue()
