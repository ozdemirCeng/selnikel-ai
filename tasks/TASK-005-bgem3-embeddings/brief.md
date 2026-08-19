# Task Brief: TASK-005 — Local BGE-M3 Dense & Sparse Embedding Service

## 1. Goal
Implement a production-grade local embedding service supporting dense and lexical/sparse vector representations using **BAAI/bge-m3** (1024-dimension dense vectors + sparse lexical weights) with multi-lingual Turkish/English capability and a resilient fallback mock/hash embedding provider for testing and offline environments.

## 2. Scope
1. **Mandatory Research (`research.md`)**:
   - Evaluate BGE-M3 multi-functionality: Dense retrieval (1024 dims), Lexical weights (sparse BM25-style term weighting), and Multi-vector (ColBERT style).
   - Evaluate memory footprint (FP16 vs FP32 vs ONNX/Torch), batching throughput, and Turkish technical term tokenization.
   - Evaluate fallback strategy when PyTorch/FlagEmbedding is loading models vs lightweight tests.
2. **Abstract Interface & Implementations**:
   - `backend/app/services/embedding/base.py`: Contract `BaseEmbeddingProvider` with `embed_documents(texts: List[str]) -> List[List[float]]`, `embed_query(text: str) -> List[float]`, `embed_sparse(texts: List[str]) -> List[Dict[int, float]]`.
   - `backend/app/services/embedding/bgem3.py`: `BGEM3EmbeddingProvider` with optional `FlagEmbedding` or `sentence-transformers` integration.
   - `backend/app/services/embedding/fallback.py`: `DeterministicHashEmbeddingProvider` providing zero-latency 1024-dim deterministic embeddings for testing and CI.
   - `backend/app/services/embedding/factory.py`: `EmbeddingProviderFactory` selecting provider based on `EMBEDDING_PROVIDER` setting (`bge-m3`, `openai`, `mock`).
3. **Automated Testing & Adversarial Review**:
   - Unit tests in `backend/tests/test_embedding.py`.
   - Adversarial review by `RAG-02`.

## 3. Acceptance Criteria
- [ ] Research artifact authored detailing BGE-M3 dense/sparse specifications.
- [ ] `BaseEmbeddingProvider` interface defined with dense and sparse signatures.
- [ ] `BGEM3EmbeddingProvider` and deterministic fallback implemented.
- [ ] `EmbeddingProviderFactory` dynamically instantiated in application lifecycle.
- [ ] Unit tests pass with 100% success.
- [ ] `RAG-02` adversarial review completed with `VERDICT: PASS`.
