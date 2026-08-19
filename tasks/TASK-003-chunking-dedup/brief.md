# Task Brief: TASK-003 — Table-Aware Hierarchical Chunking & SHA-256 Deduplication

## 1. Goal
Implement a structure-aware chunking engine and document deduplication service that converts parsed engineering documents into contextually enriched chunks while preserving tables, hierarchical headers, exact page attribution, and deduplicating documents via SHA-256 hashes.

## 2. Scope
1. **Mandatory Research (`research.md`)**:
   - Compare markdown-aware semantic chunking vs. naive token sliding windows for engineering documentation.
   - Investigate hierarchical header prepending (`# Boiler > ## Dimensions`) to preserve domain context.
   - Investigate table atomic integrity (ensuring whole markdown tables stay inside single chunks).
2. **Chunking Engine (`chunker.py`)**:
   - `TableAwareChunker`: chunks `ParsedDocument` into `DomainChunk` instances (target: 500–1000 tokens).
   - Generates and preserves all 9 required metadata fields (`document_id`, `document_version`, `filename`, `page_number`, `section`, `document_type`, `department`, `language`, `chunk_id`).
3. **Ingestion Pipeline & Deduplication (`pipeline.py`)**:
   - `IngestionPipeline`: Orchestrates file save, SHA-256 hash check in PostgreSQL, parsing via `DocumentParserFactory`, chunk generation, and database transaction.
4. **Quality & Adversarial Review**:
   - Unit tests in `backend/tests/test_chunker.py` and `test_ingestion_pipeline.py`.
   - Adversarial review by `RAG-02`.

## 3. Non-Goals
- Vector embedding generation & Qdrant upsert (handled in `TASK-005` & `TASK-006`).
- Web API endpoints (handled in `TASK-004`).

## 4. Acceptance Criteria
- [ ] Research artifact authored with concrete citations and chunking benchmarks.
- [ ] `TableAwareChunker` implemented preserving markdown tables intact and tracking source page numbers.
- [ ] All 9 chunk metadata fields strictly preserved on every `DomainChunk`.
- [ ] SHA-256 document deduplication detects identical file uploads and manages versioning.
- [ ] Automated tests pass with 100% success.
- [ ] Adversarial review by `RAG-02` completed and signed off with `VERDICT: PASS`.
