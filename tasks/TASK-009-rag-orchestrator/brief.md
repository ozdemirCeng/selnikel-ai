# Task Brief: TASK-009 — Deterministic RAG Pipeline Orchestrator

## 1. Goal
Implement the central `DeterministicRAGEngine` orchestrating query embedding, hybrid retrieval, cross-encoder reranking, grounded prompt formatting, LLM generation, citation extraction, and query telemetry logging to PostgreSQL.

## 2. Scope
1. **Mandatory Research (`research.md`)**:
   - Complete 5-step deterministic RAG execution graph (Retrieval -> RRF -> FlashRank -> LLM -> Citation Verification -> Audit Log).
   - Server-Sent Events (SSE) streaming architecture for real-time token streaming followed by a final `[CITATIONS]` payload event.
2. **Implementation (`backend/app/services/rag/engine.py`)**:
   - `DeterministicRAGEngine` with both batch `query()` and streaming `query_stream()` methods.
   - Saves query telemetry, retrieved chunk IDs, latency ms, and citations into PostgreSQL `QueryLogModel`.
3. **Automated Testing & Adversarial Review**:
   - Unit tests in `backend/tests/test_rag_engine.py`.
   - Adversarial review by `RAG-02`.

## 3. Acceptance Criteria
- [ ] Research artifact authored detailing pipeline state transitions.
- [ ] `DeterministicRAGEngine` connects hybrid retriever, FlashRank reranker, and LLM provider.
- [ ] Both batch `query()` and async streaming `query_stream()` operational.
- [ ] Telemetry logging to `QueryLogModel` verified.
- [ ] Unit tests pass with 100% success.
- [ ] Adversarial review completed with `VERDICT: PASS`.
