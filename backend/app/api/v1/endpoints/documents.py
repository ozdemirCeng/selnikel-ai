from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import logger
from app.db.models.document import DocumentChunkModel, DocumentModel
from app.db.session import get_db
from app.infrastructure.qdrant import qdrant_repo
from app.schemas.document import (
    ChunkResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
    MessageResponse,
)
from app.services.ingestion.pipeline import ingestion_pipeline

router = APIRouter()


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest a technical document",
)
async def upload_document(
    file: UploadFile = File(..., description="Document file (PDF, DOCX, MD, TXT)"),
    department: str = Form("engineering", description="Department owner"),
    document_type: str = Form("technical_specification", description="Type of document"),
    language: str = Form("tr", description="Primary document language"),
    allow_duplicate: bool = Form(False, description="Whether to re-index identical file"),
    db: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    """Upload an industrial manufacturing document.
    Coordinates SHA-256 deduplication, Docling layout parsing, structure-aware chunking,
    and PostgreSQL metadata indexing.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename must not be empty.")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty (0 bytes).")

    content_type = file.content_type or "application/octet-stream"

    try:
        doc, chunks, is_dup = await ingestion_pipeline.ingest_document(
            session=db,
            filename=file.filename,
            content=content,
            content_type=content_type,
            department=department,
            document_type=document_type,
            language=language,
            allow_duplicate=allow_duplicate,
        )

        msg = (
            "Existing document returned (SHA-256 deduplicated)."
            if is_dup
            else f"Document successfully ingested into {len(chunks)} chunks."
        )

        return DocumentUploadResponse(
            document=DocumentResponse.model_validate(doc),
            chunk_count=len(chunks),
            is_duplicate=is_dup,
            message=msg,
        )
    except Exception as e:
        logger.error(f"Upload and ingestion error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest document: {str(e)}",
        )


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List indexed documents with filters and pagination",
)
async def list_documents(
    skip: int = Query(0, ge=0, description="Offset"),
    limit: int = Query(50, ge=1, le=200, description="Limit"),
    department: Optional[str] = Query(None, description="Filter by department"),
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    db: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    """List indexed documents with optional departmental filtering."""
    query = select(DocumentModel)

    if department:
        query = query.where(DocumentModel.department == department)
    if document_type:
        query = query.where(DocumentModel.document_type == document_type)
    if status_filter:
        query = query.where(DocumentModel.status == status_filter)

    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    query = query.order_by(DocumentModel.created_at.desc()).offset(skip).limit(limit)
    res = await db.execute(query)
    docs = res.scalars().all()

    return DocumentListResponse(
        items=[DocumentResponse.model_validate(d) for d in docs],
        total=total,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document details by ID",
)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Get metadata for a specific document."""
    stmt = select(DocumentModel).where(DocumentModel.id == document_id)
    res = await db.execute(stmt)
    doc = res.scalars().first()

    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found.")

    return DocumentResponse.model_validate(doc)


@router.get(
    "/{document_id}/chunks",
    response_model=List[ChunkResponse],
    summary="Get all chunks for a document",
)
async def get_document_chunks(
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> List[ChunkResponse]:
    """Inspect all parsed chunks and section boundaries for a document."""
    # Verify document exists
    stmt = select(DocumentModel).where(DocumentModel.id == document_id)
    doc_res = await db.execute(stmt)
    if not doc_res.scalars().first():
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found.")

    chunk_stmt = (
        select(DocumentChunkModel)
        .where(DocumentChunkModel.document_id == document_id)
        .order_by(DocumentChunkModel.chunk_index.asc())
    )
    res = await db.execute(chunk_stmt)
    chunks = res.scalars().all()

    return [
        ChunkResponse(
            chunk_id=c.id,
            document_id=c.document_id,
            chunk_index=c.chunk_index,
            page_number=c.page_number,
            section=c.section,
            content=c.content,
            token_count=c.token_count,
        )
        for c in chunks
    ]


@router.delete(
    "/{document_id}",
    response_model=MessageResponse,
    summary="Delete a document and its chunks",
)
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Delete document from PostgreSQL catalog and Qdrant vector collection."""
    stmt = select(DocumentModel).where(DocumentModel.id == document_id)
    res = await db.execute(stmt)
    doc = res.scalars().first()

    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found.")

    # Delete from Qdrant
    await qdrant_repo.delete_by_document_id(document_id)

    # Delete from PostgreSQL (cascades to chunks)
    await db.delete(doc)
    await db.commit()

    logger.info(f"Deleted document '{doc.filename}' (ID: {document_id}) from database and vector index.")
    return MessageResponse(
        message=f"Document '{doc.filename}' and associated chunks successfully deleted.",
        success=True,
    )
