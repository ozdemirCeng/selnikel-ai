# Task Brief: TASK-016 — Engineering PDF Report Exporter & Vision Ingestion

## 1. Goal
Implement backend automated PDF generation for technical engineering reports synthesized by the AI agent (using ReportLab/HTML styling) and expose `POST /api/v1/agent/report/pdf`. Connect a one-click "PDF Olarak İndir (.pdf)" action in the Next.js Frontend Studio.

## 2. Scope
1. **PDF Generation Service (`backend/app/services/reporting/pdf_exporter.py`)**:
   - Compiles markdown into structured PDF documents with Selnikel header, tabular parameters, and digital verification seal.
2. **API Endpoint (`backend/app/api/v1/endpoints/agent.py`)**:
   - `POST /api/v1/agent/report/pdf`: Accepts markdown content / report request and returns streaming PDF bytes with `Content-Disposition: attachment; filename=Selnikel_Rapor.pdf`.
3. **Frontend Integration (`frontend/src/components/AgentStudio.tsx` & `frontend/src/lib/api.ts`)**:
   - `downloadPdfReport(markdownContent, filename)` triggered directly from the agent studio.
4. **Testing & Review**:
   - Unit tests in `backend/tests/test_pdf_export.py`.
   - Adversarial review by `BE-02` & `FE-02`.

## 3. Acceptance Criteria
- [ ] Backend exports valid binary PDF with tables and headers.
- [ ] Frontend triggers instant browser PDF download.
- [ ] 100% backend test pass rate.
- [ ] Adversarial review completed with `VERDICT: PASS`.
