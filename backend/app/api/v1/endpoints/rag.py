import time
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import logger
from app.db.models.query_log import QueryLogModel
from app.db.session import get_db
from app.domain.rag import RetrievalFilter
from app.schemas.rag import (
    CitationSchema,
    QueryLogResponse,
    RAGQueryRequest,
    RAGQueryResponse,
)
from app.services.rag.engine import rag_engine
from app.api.dependencies import get_current_user, require_permission
from app.domain.identity.models import User

router = APIRouter()


@router.post(
    "/query",
    response_model=RAGQueryResponse,
    summary="Execute grounded technical question answering query",
)
async def query_rag(
    request: RAGQueryRequest,
    user: User = Depends(require_permission("answer.create")),
    db: AsyncSession = Depends(get_db),
) -> RAGQueryResponse:
    """Execute end-to-end deterministic RAG query with citations and strict departmental ACL enforcement."""
    start_time = time.perf_counter()

    allowed_depts = None if ("admin" in user.role_codes or "super_admin" in user.role_codes or "*" in user.permissions) else user.department_ids

    filter_criteria = RetrievalFilter(
        department=request.department,
        document_type=request.document_type,
        document_id=request.document_id,
        document_ids=request.document_ids,
        language=request.language,
        allowed_departments=allowed_depts,
    )

    try:
        output = await rag_engine.query(
            query_text=request.query,
            top_k=request.top_k,
            filter_criteria=filter_criteria,
            session=db,
        )

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        return RAGQueryResponse(
            answer=output.answer,
            query=request.query,
            citations=[
                CitationSchema(
                    document_id=c.document_id,
                    filename=c.filename,
                    page_number=c.page_number,
                    section=c.section,
                    snippet=c.snippet,
                    score=c.score,
                )
                for c in output.citations
            ],
            sources_used=output.sources_used,
            latency_ms=latency_ms,
            llm_provider=getattr(rag_engine.llm, "provider_name", "openai"),
            llm_model=getattr(rag_engine.llm, "model_name", "gpt-4o-mini"),
        )
    except Exception as e:
        logger.error(f"RAG query execution error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process RAG query: {str(e)}",
        )


@router.post(
    "/stream",
    summary="Stream grounded technical response via SSE",
)
async def stream_rag(
    request: RAGQueryRequest,
    user: User = Depends(require_permission("answer.create")),
    db: AsyncSession = Depends(get_db),
):
    """Server-Sent Events (SSE) streaming endpoint for RAG query with ACL enforcement."""
    allowed_depts = None if ("admin" in user.role_codes or "super_admin" in user.role_codes or "*" in user.permissions) else user.department_ids

    filter_criteria = RetrievalFilter(
        department=request.department,
        document_type=request.document_type,
        document_id=request.document_id,
        document_ids=request.document_ids,
        language=request.language,
        allowed_departments=allowed_depts,
    )

    return StreamingResponse(
        rag_engine.query_stream(
            query_text=request.query,
            top_k=request.top_k,
            filter_criteria=filter_criteria,
            session=db,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/history",
    response_model=List[QueryLogResponse],
    summary="Get recent query audit history",
)
async def get_query_history(
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(require_permission("answer.create")),
    db: AsyncSession = Depends(get_db),
) -> List[QueryLogResponse]:
    """Retrieve recent query history from audit logs."""
    stmt = select(QueryLogModel).order_by(QueryLogModel.created_at.desc()).limit(limit)
    res = await db.execute(stmt)
    logs = res.scalars().all()

    return [QueryLogResponse.model_validate(log) for log in logs]
