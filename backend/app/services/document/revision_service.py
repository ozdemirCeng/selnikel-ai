"""
Document Revision & Approval Lifecycle Service.
Enforces revision immutability, superseding chain integrity, single active approved revision invariants,
and transactional outbox event dispatch.
"""
from datetime import datetime, timezone
import hashlib
from typing import Optional, List
import uuid
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.document import DocumentModel
from app.db.models.revision import DocumentRevisionModel
from app.db.models.outbox import OutboxEventModel
from app.domain.documents.models import RevisionApprovalStatus
from app.core.logging import logger


class RevisionService:
    """Manages transactional document revision transitions and approvals."""

    async def create_new_revision(
        self,
        session: AsyncSession,
        document_id: str,
        source_sha256: str,
        revision_code: str,
        supersedes_revision_id: Optional[str] = None,
        parser_name: str = "docling",
        parser_version: str = "2.120.3",
    ) -> DocumentRevisionModel:
        """Create a new draft revision for an existing technical document."""
        # Find latest revision number
        stmt = (
            select(DocumentRevisionModel)
            .where(DocumentRevisionModel.document_id == document_id)
            .order_by(DocumentRevisionModel.revision_number.desc())
        )
        res = await session.execute(stmt)
        latest = res.scalars().first()
        next_rev_num = (latest.revision_number + 1) if latest else 1

        rev = DocumentRevisionModel(
            document_id=document_id,
            revision_code=revision_code,
            revision_number=next_rev_num,
            supersedes_revision_id=supersedes_revision_id or (latest.id if latest else None),
            approval_status=RevisionApprovalStatus.DRAFT.value,
            source_sha256=source_sha256,
            parser_name=parser_name,
            parser_version=parser_version,
        )
        session.add(rev)
        await session.commit()
        await session.refresh(rev)
        logger.info(f"Created draft revision '{rev.revision_code}' for document '{document_id}'.")
        return rev

    async def approve_revision(
        self,
        session: AsyncSession,
        revision_id: str,
        approver_id: str,
    ) -> DocumentRevisionModel:
        """
        Approve revision within a single atomic PostgreSQL transaction.
        Invariants:
          1. Exclusive document row lock: SELECT id FROM documents WHERE id = :doc_id FOR UPDATE
          2. All existing 'approved' revisions under document_id are marked OBSOLETE with obsoleted_at.
          3. Target draft revision is set to APPROVED with approved_at and approved_by.
          4. Idempotent outbox event written in the same transaction for Qdrant payload synchronization.
          5. Single active approved revision per document_id physically enforced by DB partial unique index.
        """
        now = datetime.now(timezone.utc)

        # 1. Fetch target revision
        stmt = select(DocumentRevisionModel).where(DocumentRevisionModel.id == revision_id)
        res = await session.execute(stmt)
        rev = res.scalars().first()

        if not rev:
            raise ValueError(f"Revision '{revision_id}' not found.")

        # 2. Acquire exclusive lock on parent Document row to serialize concurrent approvals for this document
        doc_lock_stmt = select(DocumentModel.id).where(DocumentModel.id == rev.document_id).with_for_update()
        doc_res = await session.execute(doc_lock_stmt)
        if not doc_res.scalars().first():
            raise ValueError(f"Parent Document '{rev.document_id}' not found for revision '{revision_id}'.")

        # 3. Mark ALL currently approved revisions under this document as OBSOLETE
        obsolete_stmt = (
            update(DocumentRevisionModel)
            .where(
                DocumentRevisionModel.document_id == rev.document_id,
                DocumentRevisionModel.approval_status == RevisionApprovalStatus.APPROVED.value,
                DocumentRevisionModel.id != rev.id,
            )
            .values(
                approval_status=RevisionApprovalStatus.OBSOLETE.value,
                obsoleted_at=now,
            )
        )
        await session.execute(obsolete_stmt)

        # 4. Approve target revision
        rev.approval_status = RevisionApprovalStatus.APPROVED.value
        rev.approved_by = approver_id
        rev.approved_at = now
        rev.effective_at = now
        rev.obsoleted_at = None

        # 5. Update parent Document updated_at and active version
        doc_stmt = (
            update(DocumentModel)
            .where(DocumentModel.id == rev.document_id)
            .values(updated_at=now, version=rev.revision_number)
        )
        await session.execute(doc_stmt)

        # 6. Insert idempotent outbox event in the same transaction
        idempotency_raw = f"rev_approve:{rev.document_id}:{rev.id}:{rev.revision_number}"
        idempotency_key = hashlib.sha256(idempotency_raw.encode("utf-8")).hexdigest()

        # Check if outbox event already exists (idempotency guard)
        check_outbox = select(OutboxEventModel).where(OutboxEventModel.idempotency_key == idempotency_key)
        existing_outbox = (await session.execute(check_outbox)).scalars().first()

        if not existing_outbox:
            outbox_event = OutboxEventModel(
                event_id=str(uuid.uuid4()),
                aggregate_type="document_revision",
                aggregate_id=rev.id,
                event_type="document_revision.approved",
                idempotency_key=idempotency_key,
                payload={
                    "document_id": rev.document_id,
                    "approved_revision_id": rev.id,
                    "revision_code": rev.revision_code,
                    "revision_number": rev.revision_number,
                    "approved_by": approver_id,
                    "approved_at": now.isoformat(),
                },
                status="pending",
                retry_count=0,
                max_retries=5,
            )
            session.add(outbox_event)

        # 7. Commit atomic transaction
        await session.commit()
        await session.refresh(rev)
        logger.info(f"Revision '{rev.revision_code}' (ID: {rev.id}) approved by '{approver_id}' with outbox event.")
        return rev


revision_service = RevisionService()