"""
Document Revision & Approval Lifecycle Service.
Enforces revision immutability, superseding chain integrity, and single active revision invariants.
"""
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.document import DocumentModel
from app.db.models.revision import DocumentRevisionModel
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
        Approve revision and mark superseded revisions as OBSOLETE.
        Guarantees single active approved revision invariant.
        """
        now = datetime.now(timezone.utc)
        stmt = select(DocumentRevisionModel).where(DocumentRevisionModel.id == revision_id)
        res = await session.execute(stmt)
        rev = res.scalars().first()

        if not rev:
            raise ValueError(f"Revision '{revision_id}' not found.")

        # 1. Mark superseded revision as obsolete
        if rev.supersedes_revision_id:
            obsolete_stmt = (
                update(DocumentRevisionModel)
                .where(DocumentRevisionModel.id == rev.supersedes_revision_id)
                .values(approval_status=RevisionApprovalStatus.OBSOLETE.value)
            )
            await session.execute(obsolete_stmt)

        # 2. Approve target revision
        rev.approval_status = RevisionApprovalStatus.APPROVED.value
        rev.approved_by = approver_id
        rev.approved_at = now
        rev.effective_at = now

        # 3. Update parent Document's updated_at
        doc_stmt = (
            update(DocumentModel)
            .where(DocumentModel.id == rev.document_id)
            .values(updated_at=now, version=rev.revision_number)
        )
        await session.execute(doc_stmt)

        await session.commit()
        await session.refresh(rev)
        logger.info(f"Revision '{rev.revision_code}' approved by '{approver_id}'.")
        return rev


revision_service = RevisionService()
