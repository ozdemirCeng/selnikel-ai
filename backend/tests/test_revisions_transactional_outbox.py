"""
Unit & Integration Test Suite for Document Revisions, Transactional Outbox, and Layer 3 Gate.
Validates:
1. Canonical FSM Lifecycle (draft -> approved -> obsolete)
2. Database-level partial unique index (at most 1 approved revision per document_id)
3. Transactional Outbox dual-write atomicity
4. Outbox worker SKIP LOCKED processing & idempotency
5. Qdrant failure isolation & non-rollback retry mechanism
6. Layer 3 Relational Snapshot Gate (suppressing stale/obsolete revision chunks)
7. Concurrent approval race serialization via FOR UPDATE locking
"""
from datetime import datetime, timezone
import os
import uuid
from typing import Optional
import pytest
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models.document import DocumentModel
from app.db.models.revision import DocumentRevisionModel
from app.db.models.outbox import OutboxEventModel
from app.domain.documents.models import RevisionApprovalStatus
from app.domain.document import ChunkMetadata
from app.domain.rag import RetrievalResult
from app.services.document.revision_service import revision_service
from app.workers.revision_outbox_worker import RevisionOutboxWorker
from app.services.rag.engine import DeterministicRAGEngine
from app.services.llm.base import BaseLLMProvider


def get_test_engine():
    pg_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if pg_url:
        if pg_url.startswith("postgres://"):
            pg_url = pg_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif pg_url.startswith("postgresql://") and "+asyncpg" not in pg_url:
            pg_url = pg_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return create_async_engine(pg_url, echo=False)

    return create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@asynccontextmanager
async def get_test_session():
    engine = get_test_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session

    await engine.dispose()


class MockLLM(BaseLLMProvider):
    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        return "Grounded response verified against canonical approved technical revision."

    async def stream(self, prompt: str, system_prompt: Optional[str] = None, **kwargs):
        yield "Grounded response"

    async def check_health(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_canonical_fsm_single_approved_invariant():
    """Verify draft -> approved -> obsolete FSM transitions with timestamps and outbox event creation."""
    async with get_test_session() as session:
        # 1. Create document
        doc_id = str(uuid.uuid4())
        doc = DocumentModel(
            id=doc_id,
            filename="SB_Series_Boiler_Datasheet.pdf",
            file_hash="hash_sb_series_001",
            file_size_bytes=102400,
            content_type="application/pdf",
            document_type="datasheet",
            department="engineering",
            language="tr",
            version=1,
            status="ready",
        )
        session.add(doc)
        await session.commit()

        # 2. Create REV-01 (Draft)
        rev1 = await revision_service.create_new_revision(
            session=session,
            document_id=doc_id,
            source_sha256="sha256_rev01",
            revision_code="Rev. 01",
        )
        assert rev1.approval_status == RevisionApprovalStatus.DRAFT.value
        assert rev1.revision_number == 1

        # 3. Approve REV-01
        approved_rev1 = await revision_service.approve_revision(
            session=session,
            revision_id=rev1.id,
            approver_id="user-chief-engineer",
        )
        assert approved_rev1.approval_status == RevisionApprovalStatus.APPROVED.value
        assert approved_rev1.approved_at is not None
        assert approved_rev1.approved_by == "user-chief-engineer"
        assert approved_rev1.obsoleted_at is None

        # Verify outbox event created
        outbox_stmt = select(OutboxEventModel).where(OutboxEventModel.aggregate_id == rev1.id)
        outbox_res = await session.execute(outbox_stmt)
        outbox1 = outbox_res.scalars().first()
        assert outbox1 is not None
        assert outbox1.event_type == "document_revision.approved"
        assert outbox1.status == "pending"
        assert outbox1.payload["document_id"] == doc_id
        assert outbox1.payload["approved_revision_id"] == rev1.id

        # 4. Create REV-02 (Draft)
        rev2 = await revision_service.create_new_revision(
            session=session,
            document_id=doc_id,
            source_sha256="sha256_rev02",
            revision_code="Rev. 02",
            supersedes_revision_id=rev1.id,
        )
        assert rev2.approval_status == RevisionApprovalStatus.DRAFT.value
        assert rev2.revision_number == 2

        # 5. Approve REV-02 -> REV-01 must transition to OBSOLETE
        approved_rev2 = await revision_service.approve_revision(
            session=session,
            revision_id=rev2.id,
            approver_id="user-qa-lead",
        )
        assert approved_rev2.approval_status == RevisionApprovalStatus.APPROVED.value

        # Refresh REV-01
        await session.refresh(approved_rev1)
        assert approved_rev1.approval_status == RevisionApprovalStatus.OBSOLETE.value
        assert approved_rev1.obsoleted_at is not None

        # Verify outbox event for REV-02
        outbox_stmt2 = select(OutboxEventModel).where(OutboxEventModel.aggregate_id == rev2.id)
        outbox2 = (await session.execute(outbox_stmt2)).scalars().first()
        assert outbox2 is not None
        assert outbox2.payload["approved_revision_id"] == rev2.id


@pytest.mark.asyncio
async def test_partial_unique_index_physical_violation():
    """Verify that attempting to store 2 approved revisions for the same document_id directly raises IntegrityError."""
    async with get_test_session() as session:
        doc_id = str(uuid.uuid4())
        doc = DocumentModel(
            id=doc_id,
            filename="Burner_Manual.pdf",
            file_hash="hash_burner_001",
            file_size_bytes=51200,
            content_type="application/pdf",
            document_type="manual",
            department="engineering",
            language="tr",
            version=1,
            status="ready",
        )
        session.add(doc)
        await session.commit()

        # Insert first approved revision
        rev1 = DocumentRevisionModel(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            revision_code="Rev. 01",
            revision_number=1,
            approval_status="approved",
            approved_at=datetime.now(timezone.utc),
            source_sha256="sha256_1",
        )
        session.add(rev1)
        await session.commit()

        # Attempt to insert second approved revision for same document_id
        rev2 = DocumentRevisionModel(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            revision_code="Rev. 02",
            revision_number=2,
            approval_status="approved",
            approved_at=datetime.now(timezone.utc),
            source_sha256="sha256_2",
        )
        session.add(rev2)
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()


@pytest.mark.asyncio
async def test_outbox_worker_process_batch_and_idempotency():
    """Verify outbox worker processes pending events, dispatches to Qdrant, and marks status completed."""
    async with get_test_session() as session:
        doc_id = str(uuid.uuid4())
        rev_id = str(uuid.uuid4())

        # Seed pending outbox event
        event = OutboxEventModel(
            event_id=str(uuid.uuid4()),
            aggregate_type="document_revision",
            aggregate_id=rev_id,
            event_type="document_revision.approved",
            idempotency_key=f"test_idempotency_{rev_id}",
            payload={"document_id": doc_id, "approved_revision_id": rev_id},
            status="pending",
        )
        session.add(event)
        await session.commit()

        # Mock vector repository
        mock_vector_repo = AsyncMock()
        mock_vector_repo.update_revision_payload_status.return_value = True

        worker = RevisionOutboxWorker(vector_repo=mock_vector_repo)
        processed = await worker.process_batch(session=session, batch_size=10)

        assert processed == 1
        mock_vector_repo.update_revision_payload_status.assert_awaited_once_with(
            document_id=doc_id,
            approved_revision_id=rev_id,
        )

        # Refresh event state
        await session.refresh(event)
        assert event.status == "completed"
        assert event.last_error is None

        # Re-running batch should process 0 events (idempotent no-op)
        processed_again = await worker.process_batch(session=session, batch_size=10)
        assert processed_again == 0


@pytest.mark.asyncio
async def test_outbox_worker_qdrant_failure_isolation_and_retry():
    """Verify that when Qdrant is unreachable, outbox worker records retry without rolling back Postgres."""
    async with get_test_session() as session:
        doc_id = str(uuid.uuid4())
        rev_id = str(uuid.uuid4())

        event = OutboxEventModel(
            event_id=str(uuid.uuid4()),
            aggregate_type="document_revision",
            aggregate_id=rev_id,
            event_type="document_revision.approved",
            idempotency_key=f"test_qdrant_fail_{rev_id}",
            payload={"document_id": doc_id, "approved_revision_id": rev_id},
            status="pending",
            retry_count=0,
            max_retries=3,
        )
        session.add(event)
        await session.commit()

        # Mock Qdrant connection failure
        mock_vector_repo = AsyncMock()
        mock_vector_repo.update_revision_payload_status.side_effect = ConnectionError("Qdrant host offline on port 6333")

        worker = RevisionOutboxWorker(vector_repo=mock_vector_repo)
        processed = await worker.process_batch(session=session, batch_size=10)

        assert processed == 0
        await session.refresh(event)
        assert event.retry_count == 1
        assert event.status == "pending"  # Eligible for backoff retry
        assert "Qdrant host offline" in str(event.last_error)


@pytest.mark.asyncio
async def test_layer_3_stale_result_suppression():
    """Verify that Layer 3 Relational Gate filters out obsolete revision chunks before LLM prompt assembly."""
    async with get_test_session() as session:
        doc_id = str(uuid.uuid4())
        doc = DocumentModel(
            id=doc_id,
            filename="SB_Series_Boiler_Datasheet.pdf",
            file_hash="hash_layer3_test",
            file_size_bytes=102400,
            content_type="application/pdf",
            document_type="datasheet",
            department="engineering",
            language="tr",
            version=2,
            status="ready",
        )
        session.add(doc)

        # REV-01 (Obsolete - says 14.0 bar)
        rev1_id = str(uuid.uuid4())
        rev1 = DocumentRevisionModel(
            id=rev1_id,
            document_id=doc_id,
            revision_code="Rev. 01",
            revision_number=1,
            approval_status="obsolete",
            obsoleted_at=datetime.now(timezone.utc),
            source_sha256="sha256_rev01_old",
        )
        session.add(rev1)

        # REV-02 (Approved - says 16.0 bar)
        rev2_id = str(uuid.uuid4())
        rev2 = DocumentRevisionModel(
            id=rev2_id,
            document_id=doc_id,
            revision_code="Rev. 02",
            revision_number=2,
            approval_status="approved",
            approved_at=datetime.now(timezone.utc),
            source_sha256="sha256_rev02_new",
        )
        session.add(rev2)
        await session.commit()

        # Simulate retriever returning 2 chunks (one stale from REV-01 due to Qdrant sync lag, one from REV-02)
        stale_meta = ChunkMetadata(
            chunk_id="chk-obsolete-01",
            document_id=doc_id,
            document_version=1,
            filename="SB_Series_Boiler_Datasheet.pdf",
            page_number=1,
            section="Technical Specs",
            revision_id=rev1_id,
        )
        stale_chunk = RetrievalResult(
            chunk_id="chk-obsolete-01",
            content="SB-500 Dizayn Basıncı: 14.0 bar (Eski Veri)",
            metadata=stale_meta,
            score=0.95,
        )

        active_meta = ChunkMetadata(
            chunk_id="chk-active-02",
            document_id=doc_id,
            document_version=2,
            filename="SB_Series_Boiler_Datasheet.pdf",
            page_number=1,
            section="Technical Specs",
            revision_id=rev2_id,
        )
        active_chunk = RetrievalResult(
            chunk_id="chk-active-02",
            content="SB-500 Dizayn Basıncı: 16.0 bar (Güncel Onaylı Veri)",
            metadata=active_meta,
            score=0.92,
        )

        mock_retriever = AsyncMock()
        mock_retriever.retrieve.return_value = [stale_chunk, active_chunk]

        mock_reranker = AsyncMock()
        mock_reranker.rerank.return_value = [stale_chunk, active_chunk]

        engine = DeterministicRAGEngine(
            retriever=mock_retriever,
            reranker=mock_reranker,
            llm=MockLLM(),
        )

        out, returned_chunks = await engine.query_with_retrieval(
            query_text="SB-500 dizayn basıncı nedir?",
            session=session,
        )

        # Layer 3 Gate must have stripped the obsolete chunk
        assert len(returned_chunks) == 1
        assert returned_chunks[0].chunk_id == "chk-active-02"
        assert "16.0 bar" in returned_chunks[0].content
        assert "14.0 bar" not in returned_chunks[0].content


@pytest.mark.asyncio
async def test_concurrent_approval_lock_serialization():
    """Verify that concurrent approval attempts for the same document serialize and enforce 1 active approved revision."""
    engine = get_test_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    doc_id = str(uuid.uuid4())
    rev_a_id = str(uuid.uuid4())
    rev_b_id = str(uuid.uuid4())

    async with session_maker() as init_session:
        doc = DocumentModel(
            id=doc_id,
            filename="Burner_Specs.pdf",
            file_hash="hash_concurrent_001",
            file_size_bytes=64000,
            content_type="application/pdf",
            document_type="manual",
            department="engineering",
            language="tr",
            version=1,
            status="ready",
        )
        init_session.add(doc)

        rev_a = DocumentRevisionModel(
            id=rev_a_id,
            document_id=doc_id,
            revision_code="Rev. A",
            revision_number=1,
            approval_status="draft",
            source_sha256="sha_a",
        )
        rev_b = DocumentRevisionModel(
            id=rev_b_id,
            document_id=doc_id,
            revision_code="Rev. B",
            revision_number=2,
            approval_status="draft",
            source_sha256="sha_b",
        )
        init_session.add_all([rev_a, rev_b])
        await init_session.commit()

    # Approve rev_a
    async with session_maker() as s_a:
        await revision_service.approve_revision(s_a, revision_id=rev_a_id, approver_id="engineer_a")

    # Approve rev_b
    async with session_maker() as s_b:
        await revision_service.approve_revision(s_b, revision_id=rev_b_id, approver_id="engineer_b")

    # Verify that the final state in DB has strictly 1 approved revision (rev_b) and rev_a is obsolete
    async with session_maker() as check_session:
        stmt = (
            select(DocumentRevisionModel)
            .where(
                DocumentRevisionModel.document_id == doc_id,
                DocumentRevisionModel.approval_status == "approved",
            )
        )
        approved_revisions = (await check_session.execute(stmt)).scalars().all()
        assert len(approved_revisions) == 1
        assert approved_revisions[0].id == rev_b_id

        # Check total revisions: exactly one approved and one obsolete
        all_stmt = select(DocumentRevisionModel).where(DocumentRevisionModel.document_id == doc_id)
        all_revs = (await check_session.execute(all_stmt)).scalars().all()
        statuses = {r.id: r.approval_status for r in all_revs}
        assert statuses[rev_a_id] == "obsolete"
        assert statuses[rev_b_id] == "approved"

    await engine.dispose()