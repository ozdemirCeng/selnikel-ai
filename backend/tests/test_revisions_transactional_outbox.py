"""
Unit & Integration Test Suite for Document Revisions, Transactional Outbox, and Layer 3 Gate.
Validates:
1. Canonical FSM Lifecycle (draft -> approved -> obsolete), invalid transition rejection, and idempotent approved return.
2. Database-level partial unique index (at most 1 approved revision per document_id)
3. Transactional Outbox dual-write atomicity
4. Outbox worker SKIP LOCKED processing & idempotency
5. Qdrant failure isolation, exponential backoff, and next_attempt_at scheduling
6. Qdrant search payload hydration (revision_id, approval_status, etc.)
7. Layer 3 Relational Snapshot Gate Fail-Closed safety:
   - Suppressing stale/obsolete chunks
   - Suppressing document chunks lacking required revision_id (missing hydration / legacy bypass defense)
   - DB connection error safety
   - Unapproved document safety
8. Concurrent approval race serialization via FOR UPDATE locking and partial unique index
"""
import asyncio
from datetime import datetime, timezone, timedelta
import os
import uuid
from typing import Optional
import pytest
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool, NullPool

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
from app.infrastructure.qdrant import QdrantVectorRepository


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

        # 1. Create REV-01 (Draft)
        rev1 = await revision_service.create_new_revision(
            session=session,
            document_id=doc_id,
            source_sha256="sha256_rev01",
            revision_code="Rev. 01",
        )
        assert rev1.approval_status == RevisionApprovalStatus.DRAFT.value
        assert rev1.revision_number == 1

        # 2. Approve REV-01
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
        outbox1 = (await session.execute(outbox_stmt)).scalars().first()
        assert outbox1 is not None
        assert outbox1.event_type == "document_revision.approved"
        assert outbox1.status == "pending"
        assert outbox1.payload["document_id"] == doc_id
        assert outbox1.payload["approved_revision_id"] == rev1.id

        # 3. Create REV-02 (Draft)
        rev2 = await revision_service.create_new_revision(
            session=session,
            document_id=doc_id,
            source_sha256="sha256_rev02",
            revision_code="Rev. 02",
            supersedes_revision_id=rev1.id,
        )
        assert rev2.approval_status == RevisionApprovalStatus.DRAFT.value
        assert rev2.revision_number == 2

        # 4. Approve REV-02 -> REV-01 must transition to OBSOLETE
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
async def test_fsm_invalid_transition_rejection_and_idempotent_approved():
    """Verify that obsolete revisions cannot be approved, and approved revisions return idempotently."""
    async with get_test_session() as session:
        doc_id = str(uuid.uuid4())
        doc = DocumentModel(
            id=doc_id,
            filename="SB_Series_Boiler_Datasheet.pdf",
            file_hash="hash_fsm_test_001",
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

        # 1. Create and approve REV-01
        rev1 = await revision_service.create_new_revision(
            session=session,
            document_id=doc_id,
            source_sha256="sha256_rev01",
            revision_code="Rev. 01",
        )
        approved_rev1 = await revision_service.approve_revision(
            session=session,
            revision_id=rev1.id,
            approver_id="chief_eng",
        )
        assert approved_rev1.approval_status == "approved"

        # 2. Idempotent re-approval of REV-01 should succeed as no-op
        idempotent_rev1 = await revision_service.approve_revision(
            session=session,
            revision_id=rev1.id,
            approver_id="chief_eng",
        )
        assert idempotent_rev1.id == rev1.id
        assert idempotent_rev1.approval_status == "approved"

        # 3. Create and approve REV-02, making REV-01 obsolete
        rev2 = await revision_service.create_new_revision(
            session=session,
            document_id=doc_id,
            source_sha256="sha256_rev02",
            revision_code="Rev. 02",
        )
        await revision_service.approve_revision(
            session=session,
            revision_id=rev2.id,
            approver_id="chief_eng",
        )

        await session.refresh(rev1)
        assert rev1.approval_status == "obsolete"

        # 4. Attempting to approve obsolete REV-01 must raise ValueError (FSM invariant violation)
        with pytest.raises(ValueError, match="Invalid FSM transition"):
            await revision_service.approve_revision(
                session=session,
                revision_id=rev1.id,
                approver_id="chief_eng",
            )


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
        assert event.next_attempt_at is None

        # Re-running batch should process 0 events (idempotent no-op)
        processed_again = await worker.process_batch(session=session, batch_size=10)
        assert processed_again == 0


@pytest.mark.asyncio
async def test_outbox_worker_exponential_backoff_and_next_attempt_at():
    """Verify that failed outbox events calculate exponential backoff next_attempt_at and are skipped until due."""
    async with get_test_session() as session:
        doc_id = str(uuid.uuid4())
        rev_id = str(uuid.uuid4())

        event = OutboxEventModel(
            event_id=str(uuid.uuid4()),
            aggregate_type="document_revision",
            aggregate_id=rev_id,
            event_type="document_revision.approved",
            idempotency_key=f"test_backoff_{rev_id}",
            payload={"document_id": doc_id, "approved_revision_id": rev_id},
            status="pending",
            retry_count=0,
            max_retries=3,
        )
        session.add(event)
        await session.commit()

        # 1. Mock Qdrant connection failure
        mock_vector_repo = AsyncMock()
        mock_vector_repo.update_revision_payload_status.side_effect = ConnectionError("Qdrant host offline on port 6333")

        worker = RevisionOutboxWorker(
            vector_repo=mock_vector_repo,
            base_backoff_seconds=2.0,
            max_backoff_seconds=30.0,
        )

        # Process batch: event should fail and schedule backoff
        now_before = datetime.now(timezone.utc)
        processed = await worker.process_batch(session=session, batch_size=10)
        assert processed == 0

        await session.refresh(event)
        assert event.retry_count == 1
        assert event.status == "pending"
        assert event.next_attempt_at is not None
        next_attempt = event.next_attempt_at
        if next_attempt.tzinfo is None:
            next_attempt = next_attempt.replace(tzinfo=timezone.utc)
        # Backoff: 2.0 * (2^0) = 2.0s
        assert next_attempt >= now_before + timedelta(seconds=1.5)

        # 2. Immediately re-running batch must skip this event because next_attempt_at > now
        processed_immediate = await worker.process_batch(session=session, batch_size=10)
        assert processed_immediate == 0
        assert mock_vector_repo.update_revision_payload_status.call_count == 1  # Not called again

        # 3. Simulate passage of time: set next_attempt_at to past
        event.next_attempt_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        await session.commit()

        # Fix Qdrant repo to succeed
        mock_vector_repo.update_revision_payload_status.side_effect = None
        mock_vector_repo.update_revision_payload_status.return_value = True

        processed_due = await worker.process_batch(session=session, batch_size=10)
        assert processed_due == 1

        await session.refresh(event)
        assert event.status == "completed"
        assert event.next_attempt_at is None


@pytest.mark.asyncio
async def test_qdrant_search_hydration_and_e2e_stale_suppression():
    """Verify QdrantVectorRepository.search hydrations include revision_id and Layer 3 suppresses stale chunks end-to-end."""
    async with get_test_session() as session:
        doc_id = str(uuid.uuid4())
        doc = DocumentModel(
            id=doc_id,
            filename="SB_Series_Boiler_Datasheet.pdf",
            file_hash="hash_qdrant_hydrate_test",
            file_size_bytes=102400,
            content_type="application/pdf",
            document_type="datasheet",
            department="engineering",
            language="tr",
            version=2,
            status="ready",
        )
        session.add(doc)

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

        # Mock Qdrant client search returning hits with revision_id in payload
        qdrant_repo_inst = QdrantVectorRepository()
        mock_hit_stale = MagicMock()
        mock_hit_stale.id = "chunk_hit_stale_01"
        mock_hit_stale.score = 0.95
        mock_hit_stale.payload = {
            "content": "SB-500 Dizayn Basıncı: 14.0 bar (Eski Veri)",
            "document_id": doc_id,
            "revision_id": rev1_id,
            "revision_code": "Rev. 01",
            "approval_status": "obsolete",
            "filename": "SB_Series_Boiler_Datasheet.pdf",
            "page_number": 1,
            "department": "engineering",
        }

        mock_hit_active = MagicMock()
        mock_hit_active.id = "chunk_hit_active_02"
        mock_hit_active.score = 0.93
        mock_hit_active.payload = {
            "content": "SB-500 Dizayn Basıncı: 16.0 bar (Güncel Onaylı Veri)",
            "document_id": doc_id,
            "revision_id": rev2_id,
            "revision_code": "Rev. 02",
            "approval_status": "approved",
            "filename": "SB_Series_Boiler_Datasheet.pdf",
            "page_number": 1,
            "department": "engineering",
        }

        mock_client = AsyncMock()
        mock_client.search.return_value = [mock_hit_stale, mock_hit_active]
        qdrant_repo_inst._async_client = mock_client

        # 1. Verify Qdrant search correctly hydrates revision_id in ChunkMetadata
        search_results = await qdrant_repo_inst.search(query_vector=[0.1] * 1024)
        assert len(search_results) == 2
        assert search_results[0].metadata.revision_id == rev1_id
        assert search_results[0].metadata.approval_status == "obsolete"
        assert search_results[1].metadata.revision_id == rev2_id
        assert search_results[1].metadata.approval_status == "approved"

        # 2. Pass hydrated chunks to DeterministicRAGEngine with DB session
        mock_retriever = AsyncMock()
        mock_retriever.retrieve.return_value = search_results

        mock_reranker = AsyncMock()
        mock_reranker.rerank.return_value = search_results

        engine = DeterministicRAGEngine(
            retriever=mock_retriever,
            reranker=mock_reranker,
            llm=MockLLM(),
        )

        out, returned_chunks = await engine.query_with_retrieval(
            query_text="SB-500 dizayn basıncı nedir?",
            session=session,
        )

        # Layer 3 Gate must have suppressed the obsolete chunk (rev1_id)
        assert len(returned_chunks) == 1
        assert returned_chunks[0].chunk_id == "chunk_hit_active_02"
        assert "16.0 bar" in returned_chunks[0].content
        assert "14.0 bar" not in returned_chunks[0].content


@pytest.mark.asyncio
async def test_layer_3_suppresses_document_chunk_missing_revision_id():
    """Verify Layer 3 Gate enforces fail-closed suppression when a chunk has document_id but missing revision_id."""
    async with get_test_session() as session:
        doc_id = str(uuid.uuid4())
        doc = DocumentModel(
            id=doc_id,
            filename="SB_Series_Boiler_Datasheet.pdf",
            file_hash="hash_missing_rev_test",
            file_size_bytes=102400,
            content_type="application/pdf",
            document_type="datasheet",
            department="engineering",
            language="tr",
            version=1,
            status="ready",
        )
        session.add(doc)

        rev_id = str(uuid.uuid4())
        rev = DocumentRevisionModel(
            id=rev_id,
            document_id=doc_id,
            revision_code="Rev. 01",
            revision_number=1,
            approval_status="approved",
            approved_at=datetime.now(timezone.utc),
            source_sha256="sha256_approved_01",
        )
        session.add(rev)
        await session.commit()

        # Construct a candidate chunk that carries document_id but has NO revision_id (legacy/stale bypass attempt)
        stale_bypass_chunk = RetrievalResult(
            chunk_id="chunk_stale_bypass",
            content="SB-500 Çalışma Sıcaklığı: 180 C (Eski payload)",
            metadata=ChunkMetadata(
                chunk_id="chunk_stale_bypass",
                document_id=doc_id,
                revision_id=None,  # Missing revision_id!
                filename="SB_Series_Boiler_Datasheet.pdf",
                page_number=1,
                department="engineering",
            ),
            score=0.92,
        )

        mock_retriever = AsyncMock()
        mock_retriever.retrieve.return_value = [stale_bypass_chunk]

        mock_reranker = AsyncMock()
        mock_reranker.rerank.return_value = [stale_bypass_chunk]

        engine = DeterministicRAGEngine(
            retriever=mock_retriever,
            reranker=mock_reranker,
            llm=MockLLM(),
        )

        out = await engine.query(
            query_text="SB-500 çalışma sıcaklığı nedir?",
            session=session,
        )

        # Must fail-closed: return safe abstention because unversioned managed chunk was dropped
        assert "Belge revizyon doğrulaması sağlanamadığı" in out.answer
        assert len(out.citations) == 0


@pytest.mark.asyncio
async def test_layer_3_fail_closed_on_db_error_and_unapproved_doc():
    """Verify Layer 3 Gate enforces fail-closed abstention when DB errors or unapproved docs occur."""
    doc_id = str(uuid.uuid4())
    chunk = RetrievalResult(
        chunk_id="chk_unverified_01",
        content="SB-500 Kritik Teknik Parametre: 16.0 bar",
        metadata=ChunkMetadata(
            chunk_id="chk_unverified_01",
            document_id=doc_id,
            revision_id="unverified_rev_id",
            filename="SB_Series_Boiler_Datasheet.pdf",
            page_number=1,
            department="engineering",
        ),
        score=0.90,
    )

    mock_retriever = AsyncMock()
    mock_retriever.retrieve.return_value = [chunk]

    mock_reranker = AsyncMock()
    mock_reranker.rerank.return_value = [chunk]

    engine = DeterministicRAGEngine(
        retriever=mock_retriever,
        reranker=mock_reranker,
        llm=MockLLM(),
    )

    # 1. Simulate DB query failure in session
    failing_session = AsyncMock()
    failing_session.execute.side_effect = RuntimeError("Database connection lost during revision verification")

    out = await engine.query(
        query_text="SB-500 kritik parametre nedir?",
        session=failing_session,
    )
    # Must return safe fail-closed abstention
    assert "Belge revizyon doğrulaması sağlanamadığı" in out.answer
    assert len(out.citations) == 0

    # 2. Simulate valid DB session but document has no approved revisions
    async with get_test_session() as session:
        out2 = await engine.query(
            query_text="SB-500 kritik parametre nedir?",
            session=session,
        )
        assert "Belge revizyon doğrulaması sağlanamadığı" in out2.answer
        assert len(out2.citations) == 0


@pytest.mark.asyncio
async def test_concurrent_approval_race_condition(tmp_path):
    """Verify that concurrent approval attempts for the same document serialize and enforce exactly 1 active approved revision."""
    pg_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if pg_url:
        if pg_url.startswith("postgres://"):
            pg_url = pg_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif pg_url.startswith("postgresql://") and "+asyncpg" not in pg_url:
            pg_url = pg_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        engine = create_async_engine(pg_url, echo=False)
    else:
        db_file = tmp_path / f"test_concurrent_{uuid.uuid4().hex[:8]}.db"
        db_url = f"sqlite+aiosqlite:///{db_file.as_posix()}"
        engine = create_async_engine(
            db_url,
            echo=False,
            poolclass=NullPool,
        )

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
            file_hash="hash_concurrent_race_001",
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

    # Run concurrent approval attempts across distinct async sessions/connections
    async def approve_candidate(r_id: str, approver: str):
        async with session_maker() as sess:
            return await revision_service.approve_revision(sess, revision_id=r_id, approver_id=approver)

    results = await asyncio.gather(
        approve_candidate(rev_a_id, "engineer_a"),
        approve_candidate(rev_b_id, "engineer_b"),
        return_exceptions=True,
    )
    exceptions = [r for r in results if isinstance(r, Exception)]
    successes = [r for r in results if not isinstance(r, Exception)]
    # At least one approval succeeds or the concurrent conflict is serialized/rejected
    assert len(successes) >= 1

    async with session_maker() as check_session:
        all_stmt = select(DocumentRevisionModel).where(DocumentRevisionModel.document_id == doc_id)
        all_revs = (await check_session.execute(all_stmt)).scalars().all()
        approved_revs = [r for r in all_revs if r.approval_status == "approved"]
        # Database strictly contains exactly 1 approved revision
        assert len(approved_revs) == 1

    await engine.dispose()