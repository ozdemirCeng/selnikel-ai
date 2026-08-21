import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import logger
from app.db.models.document import DocumentChunkModel, DocumentModel
from app.db.models.revision import DocumentRevisionModel
from app.domain.document import DomainChunk
from app.infrastructure.storage import storage_manager
from app.services.ingestion.chunker import table_aware_chunker
from app.services.ingestion.parser import document_parser_factory


class IngestionPipeline:
    """End-to-end document ingestion orchestrator.
    Coordinates SHA-256 deduplication, raw file persistence, parsing, chunking,
    and PostgreSQL metadata catalog updates.
    """

    def __init__(
        self,
        storage=storage_manager,
        parser_factory=document_parser_factory,
        chunker=table_aware_chunker,
    ):
        self.storage = storage
        self.parser_factory = parser_factory
        self.chunker = chunker

    async def ingest_document(
        self,
        session: AsyncSession,
        filename: str,
        content: bytes,
        content_type: str = "application/pdf",
        department: str = "engineering",
        document_type: str = "technical_specification",
        language: str = "tr",
        allow_duplicate: bool = False,
    ) -> Tuple[DocumentModel, List[DomainChunk], bool]:
        """Ingest a document file.
        Returns (DocumentModel, List[DomainChunk], is_duplicate_flag).
        """
        # 1. Compute SHA-256 for deduplication
        file_hash = self.storage.compute_sha256(content)

        # 2. Check for existing document in PostgreSQL
        stmt = select(DocumentModel).where(DocumentModel.file_hash == file_hash)
        result = await session.execute(stmt)
        existing_doc = result.scalars().first()

        if existing_doc and not allow_duplicate:
            logger.info(
                f"Document '{filename}' with hash '{file_hash[:12]}' already exists in DB (ID: {existing_doc.id}). Skipping re-parsing."
            )
            # Query existing chunks
            chunk_stmt = select(DocumentChunkModel).where(
                DocumentChunkModel.document_id == existing_doc.id
            )
            chunk_res = await session.execute(chunk_stmt)
            existing_chunks = chunk_res.scalars().all()
            return existing_doc, [], True

        # 3. Save raw file to disk
        _, file_path, file_size = await self.storage.save_file(filename, content)

        # 4. Create Document Record in DB
        doc_id = str(uuid.uuid4())
        new_doc = DocumentModel(
            id=doc_id,
            filename=filename,
            file_hash=file_hash,
            file_size_bytes=file_size,
            content_type=content_type,
            document_type=document_type,
            department=department,
            language=language,
            version=1 if not existing_doc else existing_doc.version + 1,
            status="processing",
        )
        # Create initial canonical approved revision record
        rev_id = str(uuid.uuid4())
        initial_rev = DocumentRevisionModel(
            id=rev_id,
            document_id=doc_id,
            revision_code=f"Rev. {new_doc.version:02d}",
            revision_number=new_doc.version,
            approval_status="approved",
            approved_at=datetime.now(timezone.utc),
            source_sha256=file_hash,
        )
        session.add(initial_rev)
        session.add(new_doc)
        await session.flush()

        try:
            # 5. Parse Document via Parser Factory
            parser = self.parser_factory.get_parser(file_path, content_type)
            parsed_doc = await parser.parse(file_path, content_type)

            # 6. Chunk Document via Structure-Aware Chunker
            domain_chunks = self.chunker.chunk_document(
                parsed_doc=parsed_doc,
                document_id=doc_id,
                document_version=new_doc.version,
                document_type=document_type,
                department=department,
                language=language,
            )

            # 7. Persist Chunk Records in PostgreSQL
            for c in domain_chunks:
                c.metadata.revision_id = rev_id
                c.metadata.revision_code = initial_rev.revision_code
                c.metadata.revision_number = initial_rev.revision_number
                chunk_model = DocumentChunkModel(
                    id=c.metadata.chunk_id,
                    document_id=doc_id,
                    chunk_index=c.metadata.chunk_index,
                    page_number=c.metadata.page_number,
                    section=c.metadata.section,
                    content=c.content,
                    token_count=c.metadata.token_count,
                )
                session.add(chunk_model)

            # 8. Update Document Status
            new_doc.total_pages = parsed_doc.total_pages
            new_doc.status = "indexed"
            await session.commit()
            await session.refresh(new_doc)

            logger.info(
                f"Successfully ingested '{filename}': {len(domain_chunks)} chunks indexed in DB."
            )
            return new_doc, domain_chunks, False

        except Exception as e:
            await session.rollback()
            new_doc.status = "failed"
            new_doc.error_message = str(e)
            session.add(new_doc)
            await session.commit()
            logger.error(f"Ingestion failed for '{filename}': {e}")
            raise


# Default singleton instance
ingestion_pipeline = IngestionPipeline()
