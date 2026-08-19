# Technical Research: Hybrid Retrieval & Reciprocal Rank Fusion (RRF)

**Author**: `RES-01` (Technical Researcher)  
**Date**: 2026-08-19  
**Target Task**: `TASK-006` (Hybrid Retrieval & Metadata Filtering Engine)

---

## 1. Executive Recommendation

For **Selnikel Enerji’s technical manufacturing domain**, neither pure vector search nor pure keyword search is sufficient:
1. **Dense Vector Search (BGE-M3)**: Excels at semantic intent, conceptual matching, and cross-lingual translation ("buhar basıncı tahliyesi" $\leftrightarrow$ "steam safety relief valve").
2. **Sparse Lexical Search (BM25 / Lexical Weights)**: Excels at exact product models, part numbers, and numerical constraints (`SB-100`, `ECO-15`, `PN16`, `1400 kW`, `DN50`).
3. **Reciprocal Rank Fusion (RRF, $k=60$)**: Combines ranked lists from both dense and sparse retrievers without requiring score calibration or threshold tuning.

---

## 2. Mathematical Foundation: Reciprocal Rank Fusion (RRF)

$$RRF\_Score(d) = \sum_{m \in \{\text{dense}, \text{sparse}\}} \frac{w_m}{k + \text{rank}_m(d)}$$

Where:
- $k = 60$ (standard Cormack et al. constant preventing high-rank outliers from skewing results).
- $w_{dense} = 0.6$, $w_{sparse} = 0.4$ (configurable weighting).
- $\text{rank}_m(d) \ge 1$ is the 1-based index position of document $d$ in method $m$'s result set.

---

## 3. Metadata Pre-Filtering Architecture

To guarantee strict security and departmental isolation, filtering occurs in Qdrant **before vector distance computation** (pre-filtering):
```python
RetrievalFilter(
    department="engineering",      # Exact match or IN list
    document_type="user_manual",   # Exact match
    document_id="doc_123",         # Scoped to single document
    language="tr"                  # Language filtering
)
```
