# Task Brief: TASK-004 — Document Management API Endpoints (`/api/v1/documents`)

## 1. Goal
Implement production-ready FastAPI endpoints for uploading, listing, retrieving, inspecting chunks, and deleting engineering documents with validation, proper error responses, and database transactions.

## 2. Scope
1. **Endpoint Implementation (`backend/app/api/v1/endpoints/documents.py`)**:
   - `POST /upload`: Multipart file upload with metadata (`department`, `document_type`, `language`, `allow_duplicate`).
   - `GET /`: List indexed documents with filtering by department/document_type and pagination.
   - `GET /{document_id}`: Retrieve document metadata and processing status.
   - `GET /{document_id}/chunks`: Retrieve all parsed chunks for inspecting page attribution.
   - `DELETE /{document_id}`: Delete document and cascade delete all chunks and Qdrant points.
2. **Schemas**:
   - Update `backend/app/schemas/document.py` with `DocumentUploadResponse` and `MessageResponse`.
3. **Quality & Testing**:
   - Automated API tests in `backend/tests/test_document_api.py`.
   - Adversarial review by `BE-02`.

## 3. Acceptance Criteria
- [ ] `POST /api/v1/documents/upload` processes PDF/MD files and returns `DocumentResponse`.
- [ ] `GET /api/v1/documents` lists documents with correct pagination counts.
- [ ] `GET /api/v1/documents/{document_id}/chunks` returns chunks with page numbers and sections.
- [ ] `DELETE /api/v1/documents/{document_id}` cascades deletion properly.
- [ ] All automated tests pass with 100% success.
- [ ] Adversarial review by `BE-02` completed and signed off with `VERDICT: PASS`.
