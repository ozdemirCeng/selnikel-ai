"""
PostgreSQL / SQLite Ingestion Queue Concurrency, Lease Ownership & Backoff Integration Tests.
Validates:
1. State transitions through PostgresIngestionQueue
2. Worker lease ownership enforcement (worker B cannot hijack worker A's job)
3. Exponential backoff scheduling (next_attempt_at > now is not claimed)
4. Dead-letter queue isolation on max attempts
5. Concurrent worker claim isolation (FOR UPDATE SKIP LOCKED / concurrency contention)
"""
import os
import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.infrastructure.ingestion_queue import PostgresIngestionQueue
from app.db.models.ingestion import IngestionJobModel
from app.db.base import Base

def get_engine():
    pg_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if pg_url:
        if pg_url.startswith("postgres://"):
            pg_url = pg_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif pg_url.startswith("postgresql://") and "+asyncpg" not in pg_url:
            pg_url = pg_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return create_async_engine(pg_url, echo=False)

    if os.getenv("REQUIRE_POSTGRES_QUEUE") == "true":
        raise RuntimeError("REQUIRE_POSTGRES_QUEUE=true is set in CI but no PostgreSQL DATABASE_URL was provided!")

    return create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

@asynccontextmanager
async def get_test_session():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_queue_claim_and_progress_state_transitions():
    async with get_test_session() as session:
        queue = PostgresIngestionQueue()

        # Enqueue a job
        job = await queue.enqueue_job(
            session=session,
            document_id="doc-test-101",
            revision_id="rev-test-101",
            filename="Test_Kazan_Manual.pdf",
            file_path="/tmp/Test_Kazan_Manual.pdf",
            department_id="dept-engineering",
            file_size_bytes=2048,
            mime_type="application/pdf",
            sha256_hash="hash-101",
        )
        await session.commit()
        assert job.id is not None
        assert job.state == "queued"

        # Worker A claims job
        claimed = await queue.claim_next_job(session, worker_id="worker-A")
        await session.commit()
        assert claimed is not None
        assert claimed.id == job.id
        assert claimed.worker_lease_id == "worker-A"
        assert claimed.state == "parsing"

        # Worker A updates progress
        updated = await queue.update_progress(
            session, job_id=job.id, worker_id="worker-A", new_state="chunking", progress=35, stage="chunking"
        )
        await session.commit()
        assert updated.state == "chunking"
        assert updated.progress == 35.0

        # Worker A completes job
        completed = await queue.complete_job(session, job_id=job.id, worker_id="worker-A", chunks_count=12)
        await session.commit()
        assert completed.state == "completed"
        assert completed.progress == 100.0
        assert completed.chunks_count == 12


@pytest.mark.asyncio
async def test_queue_lease_ownership_protection():
    """Worker B must NOT be able to update or complete a job leased to Worker A."""
    async with get_test_session() as session:
        queue = PostgresIngestionQueue()

        job = await queue.enqueue_job(
            session=session,
            document_id="doc-test-102",
            revision_id="rev-test-102",
            filename="Guvenlik_El_Kitabi.pdf",
            file_path="/tmp/Guvenlik_El_Kitabi.pdf",
            department_id="dept-service",
            file_size_bytes=4096,
            mime_type="application/pdf",
            sha256_hash="hash-102",
        )
        await session.commit()

        # Worker A claims
        await queue.claim_next_job(session, worker_id="worker-A")
        await session.commit()

        # Worker B attempts progress update -> must fail
        with pytest.raises(PermissionError) as exc:
            await queue.update_progress(
                session, job_id=job.id, worker_id="worker-B", new_state="chunking", progress=50, stage="chunking"
            )
        assert "Worker lease ownership violation" in str(exc.value)


@pytest.mark.asyncio
async def test_queue_exponential_backoff_and_dead_letter():
    """Job failures must increment backoff; reaching max_attempts must move to dead_letter."""
    async with get_test_session() as session:
        queue = PostgresIngestionQueue()

        job = await queue.enqueue_job(
            session=session,
            document_id="doc-test-103",
            revision_id="rev-test-103",
            filename="Corrupt_Drawing.dwg",
            file_path="/tmp/Corrupt_Drawing.dwg",
            department_id="dept-engineering",
            file_size_bytes=1024,
            mime_type="application/pdf",
            sha256_hash="hash-103",
            max_attempts=2,
        )
        await session.commit()

        # Attempt 1 fail -> backoff scheduled in future
        claimed1 = await queue.claim_next_job(session, worker_id="worker-A")
        await session.commit()
        failed1 = await queue.fail_job(session, job_id=job.id, worker_id="worker-A", error_code="PARSER_ERR", error_message="Corrupted file header")
        await session.commit()

        assert failed1.state == "queued"  # Reset to queued for retry
        assert failed1.attempt == 1
        assert failed1.dead_letter is False
        assert failed1.next_attempt_at > datetime.now(timezone.utc)

        # Cannot be claimed immediately while next_attempt_at is in future
        reclaim_attempt = await queue.claim_next_job(session, worker_id="worker-B")
        assert reclaim_attempt is None

        # Simulate time pass: manually advance next_attempt_at
        failed1.next_attempt_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        await session.commit()

        # Attempt 2 (reaches max_attempts=2)
        claimed2 = await queue.claim_next_job(session, worker_id="worker-B")
        await session.commit()
        assert claimed2 is not None

        failed2 = await queue.fail_job(session, job_id=job.id, worker_id="worker-B", error_code="PARSER_ERR", error_message="Corrupted file header permanent")
        await session.commit()

        assert failed2.state == "failed"
        assert failed2.attempt == 2
        assert failed2.dead_letter is True  # Moved to Dead-Letter Queue


@pytest.mark.asyncio
async def test_queue_concurrent_workers_claim_isolation():
    """
    Simulate two concurrent workers attempting to claim the single available job simultaneously.
    Verifies that exactly ONE worker gets the claim, and the other receives None.
    """
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    queue = PostgresIngestionQueue()

    # Step 1: Enqueue a single job
    async with session_maker() as setup_session:
        job = await queue.enqueue_job(
            session=setup_session,
            document_id="doc-concurrent-01",
            revision_id="rev-concurrent-01",
            filename="Kazan_Sertifika.pdf",
            file_path="/tmp/Kazan_Sertifika.pdf",
            department_id="dept-quality",
            file_size_bytes=8192,
            mime_type="application/pdf",
            sha256_hash="hash-concurrent",
        )
        await setup_session.commit()
        job_id = job.id

    # Step 2: Concurrently claim using two separate sessions
    async def worker_claim(worker_id: str):
        async with session_maker() as session:
            claimed = await queue.claim_next_job(session, worker_id=worker_id)
            await session.commit()
            return worker_id, claimed

    pg_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if pg_url and engine.dialect.name == "postgresql":
        res1, res2 = await asyncio.gather(
            worker_claim("worker-1"),
            worker_claim("worker-2"),
        )
        claims = [res for res in [res1, res2] if res[1] is not None]
        nones = [res for res in [res1, res2] if res[1] is None]

        assert len(claims) == 1, "In PostgreSQL, FOR UPDATE SKIP LOCKED ensures exactly one worker claims the job"
        assert len(nones) == 1, "The competing worker must receive None"
        assert claims[0][1].id == job_id
    else:
        # SQLite in-memory dialect does not support row-level SKIP LOCKED; verify sequential claim isolation
        res1 = await worker_claim("worker-1")
        res2 = await worker_claim("worker-2")
        assert res1[1] is not None, "First worker must claim the available job"
        assert res2[1] is None, "Second worker must receive None as job is already claimed"
        assert res1[1].id == job_id

    await engine.dispose()
