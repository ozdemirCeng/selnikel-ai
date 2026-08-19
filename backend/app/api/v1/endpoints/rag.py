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

router = APIRouter()


@router.post(
    "/query",
    response_model=RAGQueryResponse,
    summary="Execute grounded technical question answering query",
)
async def query_rag(
    request: RAGQueryRequest,
    db: AsyncSession = Depends(get_db),
) -> RAGQueryResponse:
    """Execute end-to-end deterministic RAG query with citations and strict grounding."""
    start_time = time.perf_counter()

    filter_criteria = None
    if any([request.department, request.document_type, request.document_id, request.language]):
        filter_criteria = RetrievalFilter(
            department=request.department,
            document_type=request.document_type,
            document_id=request.document_id,
            language=request.language,
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
        logger.error(f"RAG query execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG execution failed: {str(e)}",
        )


@router.post(
    "/stream",
    summary="Stream grounded RAG answer via Server-Sent Events (SSE)",
)
async def stream_rag(
    request: RAGQueryRequest,
    db: AsyncSession = Depends(get_db),
):
    """Real-time SSE token stream for interactive AI assistant with live citations event."""
    filter_criteria = None
    if any([request.department, request.document_type, request.document_id, request.language]):
        filter_criteria = RetrievalFilter(
            department=request.department,
            document_type=request.document_type,
            document_id=request.document_id,
            language=request.language,
        )

    stream_generator = rag_engine.query_stream(
        query_text=request.query,
        top_k=request.top_k,
        filter_criteria=filter_criteria,
        session=db,
    )

    return StreamingResponse(
        stream_generator,
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
    summary="Get recent question answering audit history",
)
async def get_query_history(
    limit: int = Query(20, ge=1, le=100, description="Max history logs to return"),
    skip: int = Query(0, ge=0, description="Offset"),
    db: AsyncSession = Depends(get_db),
) -> List[QueryLogResponse]:
    """Retrieve audit trail of recent queries and their performance latencies."""
    stmt = (
        select(QueryLogModel)
        .order_by(QueryLogModel.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    res = await db.execute(stmt)
    logs = res.scalars().all()
    return [QueryLogResponse.model_validate(l) for l in logs]
