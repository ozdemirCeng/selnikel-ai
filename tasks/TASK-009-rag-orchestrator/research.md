# Technical Research: Deterministic RAG Pipeline Orchestrator

**Author**: `RES-01` (Technical Researcher)  
**Date**: 2026-08-19  
**Target Task**: `TASK-009` (Deterministic RAG Pipeline Orchestrator)

---

## 1. Executive Recommendation

The **Deterministic RAG Pipeline** must operate as a strict, linear, verifiable sequence:
1. **Query & Filters**: Accept natural language question and optional departmental constraints.
2. **Hybrid Candidate Retrieval**: Fetch top 15 candidates from Qdrant using dense + sparse vectors.
3. **Cross-Encoder Reranking**: Filter down to top 4 highest-relevance passages using FlashRank.
4. **Context Injection**: Assemble system prompt and numbered document context.
5. **Generation**: Stream or generate response via `BaseLLMProvider`.
6. **Citation Resolution**: Extract inline markers and map to source pages.
7. **Telemetry Persistence**: Log latency, token count, and chunk IDs to PostgreSQL `QueryLogModel`.

---

## 2. Server-Sent Events (SSE) Streaming Schema

```text
event: message
data: {"type": "token", "content": "Selnikel "}

event: message
data: {"type": "token", "content": "SB-100 "}

...

event: message
data: {"type": "citations", "citations": [{"filename": "SB100.pdf", "page_number": 3}], "sources_used": ["SB100.pdf"]}

event: message
data: [DONE]
```
