# Task Brief: TASK-006 — Hybrid Retrieval (Dense Semantic + Sparse BM25 + Qdrant RRF Fusion)

## 1. Goal
Implement a production hybrid retriever combining dense vector semantic search with sparse lexical term matching, fused via Reciprocal Rank Fusion (RRF) and pre-filtered on metadata attributes (department, document_type, language, document_id).

## 2. Scope
1. **Mandatory Research (`research.md`)**:
   - Evaluate dense semantic recall vs exact keyword precision on industrial equipment codes (`SB-100`, `DN50`, `16 bar`).
   - Formula for Reciprocal Rank Fusion ($k = 60$) and score normalization.
   - Qdrant collection payload filtering and multi-vector search execution.
2. **Implementation**:
   - `backend/app/services/retrieval/base.py`: Contract `BaseRetriever`.
   - `backend/app/services/retrieval/hybrid.py`: `QdrantHybridRetriever` with RRF fusion, metadata filtering, and domain chunk mapping.
   - `backend/app/services/retrieval/factory.py`: `RetrieverFactory`.
3. **Automated Testing & Adversarial Review**:
   - Unit tests in `backend/tests/test_hybrid_retriever.py`.
   - Adversarial review by `RAG-02`.

## 3. Acceptance Criteria
- [ ] Research artifact completed with mathematical RRF formula and filter specifications.
- [ ] `BaseRetriever` interface strictly defined.
- [ ] `QdrantHybridRetriever` implemented supporting dense, sparse, and RRF fused retrieval.
- [ ] Metadata pre-filtering by `department`, `document_type`, and `document_id` supported.
- [ ] Automated tests passing 100%.
- [ ] Adversarial review signed off with `VERDICT: PASS`.
