# Task Brief: TASK-007 — FlashRank Local Cross-Encoder Reranker Integration

## 1. Goal
Implement a high-performance, local, ONNX-accelerated Cross-Encoder reranker using **FlashRank** to score $(query, passage)$ pairs with full cross-attention, boosting precision and filtering out low-relevance candidates prior to LLM generation.

## 2. Scope
1. **Mandatory Research (`research.md`)**:
   - Cross-encoder reranking principles vs. bi-encoder cosine similarity.
   - FlashRank ONNX architecture (`ms-marco-TinyBERT-L-2-v2` / `ms-marco-MiniLM-L-12-v2`), latency benchmarks (~10–20ms), and zero-PyTorch dependency.
   - Pass-through fallback when reranking is disabled.
2. **Implementation**:
   - `backend/app/services/retrieval/reranker.py`: `BaseReranker`, `FlashRankReranker`, `PassThroughReranker`, and `RerankerFactory`.
3. **Automated Testing & Adversarial Review**:
   - Unit tests in `backend/tests/test_reranker.py`.
   - Adversarial review by `RAG-02`.

## 3. Acceptance Criteria
- [ ] Research artifact authored detailing cross-encoder benchmarks.
- [ ] `BaseReranker` interface implemented with `rerank(query, results, top_n)`.
- [ ] `FlashRankReranker` and `PassThroughReranker` operational.
- [ ] Unit tests pass with 100% success.
- [ ] Adversarial review completed by `RAG-02` with `VERDICT: PASS`.
