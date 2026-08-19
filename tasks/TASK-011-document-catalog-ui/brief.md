# Task Brief: TASK-011 — Document Upload & Knowledge Catalog Explorer in Next.js 14

## 1. Goal
Implement a modern, high-precision engineering document catalog and upload interface in Next.js 14 (App Router, Tailwind CSS, Lucide icons) supporting PDF/DOCX/XLSX uploads with departmental metadata tagging, chunk inspection, and cascade document deletion.

## 2. Scope
1. **API Client & Type Definitions**:
   - `frontend/src/lib/types.ts`: `DocumentItem`, `DocumentDetail`, `DocumentChunkItem`, `DocumentUploadRequest`.
   - `frontend/src/lib/api.ts`: `uploadDocument()`, `fetchDocuments()`, `fetchDocumentChunks()`, `deleteDocument()`.
2. **Components**:
   - `frontend/src/components/DocumentUploadModal.tsx`: Drag-and-drop file upload modal with validation.
   - `frontend/src/components/DocumentCatalog.tsx`: Searchable, filterable document list with metadata badges, page counts, chunk counts, and action buttons.
   - `frontend/src/components/ChunkInspectorModal.tsx`: Modal viewing extracted chunks, token counts, headers, and preserved tables.
3. **Route**:
   - Integrated tab or `/documents` view.
4. **Verification**:
   - TypeScript compile check and `next build` validation.
   - Adversarial review by `FE-02`.

## 3. Acceptance Criteria
- [ ] Document list loads live from `/api/v1/documents`.
- [ ] Upload modal supports PDF, DOCX, XLSX with Department, Document Type, and Language selectors.
- [ ] Chunk inspector displays extracted chunks with section headers and page numbers.
- [ ] Delete action removes document and refreshes state.
- [ ] Next.js build passes with 0 TypeScript/lint errors.
- [ ] Adversarial review completed by `FE-02` with `VERDICT: PASS`.
