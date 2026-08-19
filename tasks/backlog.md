# Task Backlog

| Task ID | Title | Division | Priority | Dependencies | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `TASK-002` | Docling Industrial Parsing Engine | AI / RAG | P0 | `TASK-001` | Research & integrate Docling parser for PDF/DOCX with native table and layout extraction. |
| `TASK-003` | Structure-Aware Chunking & Deduplication | AI / RAG | P0 | `TASK-002` | Implement Markdown-aware chunking preserving tables, headers, and SHA-256 deduplication. |
| `TASK-004` | Document Ingestion API Endpoints | Backend | P0 | `TASK-003` | Complete `/api/v1/documents` endpoints (Upload, Catalog, Status, Delete). |
| `TASK-005` | Local BGE-M3 Embedding Integration | AI / RAG | P0 | `TASK-001` | Implement local multilingual BGE-M3 dense and sparse vector generation. |
| `TASK-006` | Qdrant Hybrid Retrieval & Filtering | AI / RAG | P0 | `TASK-005` | Build hybrid search (dense + sparse) with department/document_type payload filtering. |
| `TASK-007` | FlashRank Local Reranker | AI / RAG | P1 | `TASK-006` | Integrate sub-10ms CPU cross-encoder reranking to minimize RAG hallucinations. |
| `TASK-008` | Grounded Engineering Prompt & Citations | AI / RAG | P0 | `TASK-006` | Design anti-hallucination prompt and page citation extraction parser. |
| `TASK-009` | Streaming Answer Generator API | Backend | P0 | `TASK-008` | Implement `/api/v1/rag/chat/stream` SSE endpoint with citation metadata payloads. |
| `TASK-010` | Automated Evaluation Harness | QA | P1 | `TASK-009` | Build RAG Triad benchmark runner against `backend/tests/evaluation/questions.json`. |
| `TASK-011` | Document Management UI | Frontend | P0 | `TASK-004` | Next.js drag-and-drop document upload with metadata tagging and status table. |
| `TASK-012` | Interactive Chat & Citation UI | Frontend | P0 | `TASK-009` | Next.js streaming chat UI with interactive citation badges and snippet modals. |
