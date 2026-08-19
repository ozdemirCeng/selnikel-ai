# Technical Research: Local Cross-Encoder Reranking with FlashRank

**Author**: `RES-01` (Technical Researcher)  
**Date**: 2026-08-19  
**Target Task**: `TASK-007` (FlashRank Local Cross-Encoder Reranker Integration)

---

## 1. Executive Recommendation

To achieve maximum answer accuracy and eliminate irrelevant context before LLM generation in **Selnikel AI**, we implement a **two-stage retrieval pipeline**:
1. **Stage 1 (High Recall)**: `QdrantHybridRetriever` fetches the top 15–20 candidates using dense vectors + sparse lexical matching.
2. **Stage 2 (High Precision)**: **`FlashRank`** performs full cross-attention reranking on $(query, candidate)$ pairs, pruning the candidates to the top 3–5 most relevant chunks.

---

## 2. Cross-Encoder vs. Bi-Encoder Architecture

```text
Stage 1: Bi-Encoder (BGE-M3 + Qdrant)
Query ───► [Embedding] ──┐
                         ├──► Cosine Similarity (Fast, Top 20)
Chunks ──► [Embedding] ──┘
                         │
                         ▼
Stage 2: Cross-Encoder (FlashRank ONNX)
[Query + Chunk] ──► [Self-Attention Transformers] ──► Relevance Score (Ultra-Precise, Top 5)
```

| Metric | Bi-Encoder (BGE-M3) | Cross-Encoder (FlashRank) |
| :--- | :--- | :--- |
| **Input** | Query & Passage encoded separately | Query & Passage encoded together |
| **Interaction** | Dot product / Cosine similarity only | Full token-to-token cross-attention |
| **Throughput** | Millions of vectors / second | 10–50 candidate passages / 15ms |
| **Role in Pipeline** | Broad recall filter (Top 20) | Final precision ranker (Top 5) |

---

## 3. FlashRank Performance & Fallback

- **Library**: `flashrank` (ONNX Runtime, C++ optimized).
- **Latency**: $\approx 12\text{ms}$ on CPU for 10 candidates.
- **Model**: `ms-marco-TinyBERT-L-2-v2` (default, ~4MB) or `ms-marco-MiniLM-L-12-v2`.
- **Pass-Through Fallback**: If disabled or unavailable, `PassThroughReranker` preserves Stage 1 RRF ranking seamlessly.
