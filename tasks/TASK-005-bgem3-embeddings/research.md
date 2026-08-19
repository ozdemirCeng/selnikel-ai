# Technical Research: Local BGE-M3 Dense & Sparse Embedding Service

**Author**: `RES-01` (Technical Researcher)  
**Date**: 2026-08-19  
**Target Task**: `TASK-005` (Local BGE-M3 Embedding Service)

---

## 1. Executive Recommendation

For **Selnikel Enerji’s multilingual engineering documentation**, **BAAI/bge-m3** is the optimal embedding model:
1. **Multi-Functionality (M3)**: Produces both **Dense Vectors (1024 dimensions)** for semantic conceptual matching and **Sparse Lexical Vectors** for exact engineering serial numbers and part codes (e.g. `SB-100`, `ECO-200`, `16 bar`, `DIN 2448`).
2. **Multilingual Alignment**: Benchmark leader for Turkish-English technical cross-lingual semantic matching.
3. **Long Context Window**: Supports up to 8192 tokens, easily handling 600–1000 token structure-aware engineering chunks.
4. **Air-Gap / Privacy**: 100% local execution on CPU or GPU without external cloud API dependencies.

---

## 2. Model Architecture & Vector Dimensions

| Feature | BGE-M3 Specification | Selnikel Industrial Application |
| :--- | :--- | :--- |
| **Dense Embedding** | 1024 dimensions (Normalized Float32/Float16) | High-accuracy semantic search (e.g. "aşırı buhar basıncı tahliye valfi") |
| **Sparse / Lexical Embedding** | Dictionary of `{token_id: weight}` | Exact term match for product codes (`SB-100`, `3000 kg/h`, `EN 12953`) |
| **Max Sequence Length** | 8192 tokens | Ingests comprehensive tables and section hierarchies |
| **Distance Metric** | Cosine Similarity / Dot Product | Native index format in Qdrant |

---

## 3. Fast Testing & Fallback Architecture

To ensure tests execute rapidly in CI and developer environments without downloading 2.2 GB model weights during every test run:
- **`BGEM3EmbeddingProvider`**: Loads PyTorch/FlagEmbedding model in production.
- **`DeterministicHashEmbeddingProvider`**: Generates mathematically consistent 1024-dim unit vectors using deterministic token hashing for instantaneous testing and verification.
- **`EmbeddingProviderFactory`**: Automatically routes to the configured provider via `settings.EMBEDDING_PROVIDER`.
