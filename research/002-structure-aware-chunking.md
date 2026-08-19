# Research 002: Structure-Aware Hierarchical Chunking & Document Deduplication

**Author**: `RES-01` (Technical Researcher)  
**Date**: 2026-08-19  
**Referenced Task**: [`TASK-003: Table-Aware Hierarchical Chunking & SHA-256 Deduplication`](file:///c:/Users/Diley/dev/workspace/selnikel-ai/tasks/TASK-003-chunking-dedup/brief.md)

---

## 1. Executive Summary
Structure-Aware Hierarchical Chunking solves table corruption and contextual ambiguity in technical engineering RAG by:
1. Atomically preserving Markdown tables in individual chunks.
2. Prepending hierarchical section headers (`# Section > ## Subsection`) to paragraphs.
3. Enforcing SHA-256 deduplication at the database level.

*(For full benchmark tables and failure mode analyses, see the [TASK-003 Research Dossier](file:///c:/Users/Diley/dev/workspace/selnikel-ai/tasks/TASK-003-chunking-dedup/research.md)).*
