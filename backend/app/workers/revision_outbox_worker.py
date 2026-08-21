"""
Transactional Revision Outbox Worker.
Consumes outbox events using SELECT FOR UPDATE SKIP LOCKED and synchronizes vector payload states with Qdrant.
Guarantees at-least-once delivery, non-rollback transactional isolation, and exponential backoff retry.
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.db.models.outbox import OutboxEventModel
from app.infrastructure.qdrant import QdrantVectorRepository, qdrant_repo


class RevisionOutboxWorker:
    """Processes document revision outbox events and synchronizes vector payload states with exponential backoff."""

    def __init__(
        self,
        vector_repo: Optional[QdrantVectorRepository] = None,
        base_backoff_seconds: float = 2.0,
        max_backoff_seconds: float = 60.0,
    ):
        self.vector_repo = vector_repo or qdrant_repo
        self.base_backoff_seconds = base_backoff_seconds
        self.max_backoff_seconds = max_backoff_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self, session_maker, poll_interval_seconds: float = 2.0, batch_size: int = 10) -> None:
        """Start background polling loop."""
        self._running = True
        while self._running:
            try:
                async with session_maker() as session:
                    await self.process_batch(session=session, batch_size=batch_size)
            except Exception as e:
                logger.error(f"Error in RevisionOutboxWorker loop: {e}")
            await asyncio.sleep(poll_interval_seconds)

    def stop(self) -> None:
        """Signal background worker to stop."""
        self._running = False

    async def process_batch(
        self,
        session: AsyncSession,
        batch_size: int = 10,
    ) -> int:
        """
        Poll and process a batch of pending outbox events using SELECT FOR UPDATE SKIP LOCKED.
        Filters by (next_attempt_at IS NULL OR next_attempt_at <= now).
        Returns the number of processed events.
        """
        now = datetime.now(timezone.utc)
        stmt = (
            select(OutboxEventModel)
            .where(
                OutboxEventModel.status == "pending",
                or_(
                    OutboxEventModel.next_attempt_at.is_(None),
                    OutboxEventModel.next_attempt_at <= now,
                ),
            )
            .order_by(OutboxEventModel.created_at.asc())
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
        res = await session.execute(stmt)
        events = res.scalars().all()

        if not events:
            return 0

        processed_count = 0
        for event in events:
            try:
                if event.event_type == "document_revision.approved":
                    payload = event.payload or {}
                    document_id = payload.get("document_id")
                    approved_revision_id = payload.get("approved_revision_id")

                    if document_id and approved_revision_id:
                        # Synchronize Qdrant payload approval status
                        await self.vector_repo.update_revision_payload_status(
                            document_id=document_id,
                            approved_revision_id=approved_revision_id,
                        )

                event.status = "completed"
                event.locked_at = None
                event.updated_at = now
                event.last_error = None
                event.next_attempt_at = None
                processed_count += 1
                logger.info(f"Outbox event '{event.event_id}' ({event.event_type}) completed successfully.")
            except Exception as e:
                event.retry_count += 1
                event.last_error = str(e)
                event.locked_at = None
                event.updated_at = now
                if event.retry_count >= event.max_retries:
                    event.status = "failed"
                    event.next_attempt_at = None
                    logger.error(f"Outbox event '{event.event_id}' failed permanently after {event.retry_count} retries: {e}")
                else:
                    event.status = "pending"
                    backoff_delay = min(
                        self.max_backoff_seconds,
                        self.base_backoff_seconds * (2 ** (event.retry_count - 1)),
                    )
                    event.next_attempt_at = now + timedelta(seconds=backoff_delay)
                    logger.warning(
                        f"Outbox event '{event.event_id}' failed (attempt {event.retry_count}/{event.max_retries}): {e}. "
                        f"Retry scheduled at {event.next_attempt_at} (delay: {backoff_delay:.1f}s)."
                    )

        await session.commit()
        return processed_count


revision_outbox_worker = RevisionOutboxWorker()