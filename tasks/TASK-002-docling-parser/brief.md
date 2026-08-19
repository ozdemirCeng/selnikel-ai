# Task Brief: TASK-002 — Docling Industrial Parsing & Table Extraction Engine

## 1. Goal
Design and implement a robust, production-oriented document parsing engine for Selnikel AI capable of extracting structured text, preserving complex engineering tables in Markdown format, and tracking page-level boundaries from technical industrial documents (PDF, DOCX, TXT).

## 2. Scope
1. **Mandatory Research (`research.md`)**:
   - Investigate Docling (`DocumentConverter`, `DoclingDocument`), OCR fallbacks, table structure extraction, performance on multi-page engineering documents, and fallback mechanisms.
2. **Abstract Interface**:
   - `BaseDocumentParser` interface defining `parse(file_path: str, content_type: str) -> ParsedDocument`.
3. **Concrete Implementations**:
   - `DoclingParser`: Uses IBM Docling for advanced layout and table extraction with page number attribution.
   - `FastFallbackParser`: Lightweight, zero-heavy-dependency fallback for plain text, markdown, and basic documents to guarantee system resilience.
   - `DocumentParserFactory`: Dynamic resolver selecting the appropriate parser based on file type and environment configuration.
4. **Structured Domain Models**:
   - `ParsedDocument`, `ParsedPage`, `ParsedTable`, `ParsedSection`.
5. **Quality & Review**:
   - Unit tests covering table extraction, multi-page attribution, and fallback handling.
   - Adversarial review by `RAG-02`.

## 3. Non-Goals
- Chunking and vector storage (handled in `TASK-003` and `TASK-005`).
- FastAPI upload endpoints (handled in `TASK-004`).

## 4. Acceptance Criteria
- [ ] Research artifact completed with real-world citations and benchmark observations.
- [ ] `BaseDocumentParser` contract defined in `backend/app/services/ingestion/parser.py`.
- [ ] `DoclingParser` implemented extracting tables as Markdown and mapping text to source pages.
- [ ] `FastFallbackParser` implemented for high-speed fallback.
- [ ] Automated tests in `backend/tests/test_parser.py` passing with 100% success.
- [ ] `RAG-02` adversarial review completed and signed off with `VERDICT: PASS`.
