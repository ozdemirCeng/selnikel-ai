"""
PostgreSQL-Native Ingestion Queue Repository using SELECT FOR UPDATE SKIP LOCKED.
Provides durable, distributed-safe queue operations with worker heartbeats and leases.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.ingestion import IngestionJobModel
from app.core.logging import logger

class PostgresIngestionQueue:
    """PostgreSQL ACID-compliant task queue implementation."""

    async def enqueue_job(
        self,
        session: AsyncSession,
        document_id: str,
        revision_id: str,
    ) -> IngestionJobModel:
        """Enqueue a new document ingestion job."""
        job = IngestionJobModel(
            document_id=document_id,
            revision_id=revision_id,
            state="queued",
            progress=0.0,
            attempt=1,
            max_attempts=3,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        logger.info(f"Enqueued IngestionJob '{job.id}' for Document '{document_id}'.")
        return job

    async def claim_next_job(
        self,
        session: AsyncSession,
        worker_id: str,
        lease_duration_seconds: int = 300,
    ) -> Optional[IngestionJobModel]:
        """
        Claim next available job using SELECT ... FOR UPDATE SKIP LOCKED.
        Protects against multiple concurrent workers claiming the same job.
        """
        now = datetime.now(timezone.utc)
        lease_expires = now + timedelta(seconds=lease_duration_seconds)

        # Select queued or expired/abandoned jobs with remaining retry attempts
        stmt = (
            select(IngestionJobModel)
            .where(
                (IngestionJobModel.state == "queued")
                | (
                    (IngestionJobModel.state.in_(["validating", "parsing", "chunking", "embedding", "indexing"]))
                    & (IngestionJobModel.lease_expires_at < now)
                )
            )
            .where(IngestionJobModel.attempt <= IngestionJobModel.max_attempts)
            .order_by(IngestionJobModel.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )

        res = await session.execute(stmt)
        job = res.scalars().first()

        if job:
            job.worker_lease_id = worker_id
            job.lease_expires_at = lease_expires
            job.state = "validating"
            job.started_at = now
            await session.commit()
            await session.refresh(job)
            logger.info(f"Worker '{worker_id}' successfully claimed IngestionJob '{job.id}'.")
            return job

        return None

    async def renew_lease(
        self,
        session: AsyncSession,
        job_id: str,
        worker_id: str,
        extend_seconds: int = 300,
    ) -> bool:
        """Extend heartbeat lease for an active worker."""
        now = datetime.now(timezone.utc)
        new_expires = now + timedelta(seconds=extend_seconds)

        stmt = (
            update(IngestionJobModel)
            .where(IngestionJobModel.id == job_id)
            .where(IngestionJobModel.worker_lease_id == worker_id)
            .values(lease_expires_at=new_expires)
        )
        res = await session.execute(stmt)
        await session.commit()
        return res.rowcount > 0

    async def update_progress(
        self,
        session: AsyncSession,
        job_id: str,
        state: str,
        progress: float,
    ) -> None:
        """Update job stage and percentage progress."""
        stmt = (
            update(IngestionJobModel)
            .where(IngestionJobModel.id == job_id)
            .values(state=state, progress=progress)
        )
        await session.execute(stmt)
        await session.commit()

    async def complete_job(
        self,
        session: AsyncSession,
        job_id: str,
    ) -> None:
        """Mark ingestion job as successfully completed."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(IngestionJobModel)
            .where(IngestionJobModel.id == job_id)
            .values(
                state="completed",
                progress=100.0,
                completed_at=now,
                worker_lease_id=None,
                lease_expires_at=None,
            )
        )
        await session.execute(stmt)
        await session.commit()
        logger.info(f"IngestionJob '{job_id}' marked as completed.")

    async def fail_job(
        self,
        session: AsyncSession,
        job_id: str,
        error_code: str,
        error_message: str,
    ) -> None:
        """Mark job as failed or schedule retry with backoff."""
        stmt = select(IngestionJobModel).where(IngestionJobModel.id == job_id)
        res = await session.execute(stmt)
        job = res.scalars().first()

        if job:
            job.error_code = error_code
            job.error_message = error_message
            if job.attempt < job.max_attempts:
                job.attempt += 1
                job.state = "queued"  # Re-queue for retry
                job.worker_lease_id = None
                job.lease_expires_at = None
                logger.warning(f"IngestionJob '{job_id}' failed (Attempt {job.attempt}/{job.max_attempts}). Re-queued.")
            else:
                job.state = "failed"  # Dead-letter state
                job.completed_at = datetime.now(timezone.utc)
                job.worker_lease_id = None
                job.lease_expires_at = None
                logger.error(f"IngestionJob '{job_id}' permanently failed after {job.max_attempts} attempts.")
            await session.commit()


ingestion_queue = PostgresIngestionQueue()
