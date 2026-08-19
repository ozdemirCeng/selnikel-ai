# Task Brief: TASK-010 — Unified RAG Query & SSE Streaming API Endpoints

## 1. Goal
Implement high-performance FastAPI endpoints for batch Q&A queries and real-time Server-Sent Events (SSE) streaming with metadata filtering, structured citations, and query history inspection.

## 2. Scope
1. **Schemas (`backend/app/schemas/rag.py`)**:
   - `RAGQueryRequest`: `{query: str, top_k: int = 4, department: Optional[str], document_type: Optional[str], language: Optional[str]}`.
   - `RAGQueryResponse`: `{answer: str, citations: List[Citation], sources_used: List[str]}`.
   - `QueryLogResponse`: `{id: str, query_text: str, generated_answer: str, latency_ms: float, created_at: datetime}`.
2. **Endpoints (`backend/app/api/v1/endpoints/rag.py`)**:
   - `POST /api/v1/rag/query`: Batch query endpoint.
   - `POST /api/v1/rag/stream`: SSE Streaming endpoint (`text/event-stream`).
   - `GET /api/v1/rag/history`: Query log audit endpoint.
3. **Quality & Testing**:
   - Integration tests in `backend/tests/test_rag_api.py`.
   - Adversarial review by `BE-02`.

## 3. Acceptance Criteria
- [ ] `POST /api/v1/rag/query` returns structured answer and citations.
- [ ] `POST /api/v1/rag/stream` returns SSE event stream with `text/event-stream` media type.
- [ ] `GET /api/v1/rag/history` returns logged queries from PostgreSQL.
- [ ] All unit and integration tests pass with 100% success.
- [ ] Adversarial review completed by `BE-02` with `VERDICT: PASS`.
