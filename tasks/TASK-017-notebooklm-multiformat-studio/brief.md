# Task Brief: TASK-017 — NotebookLM Multi-Format Studio & Exporters

## 1. Goal
Implement a Google NotebookLM-style 3-pane workstation with multi-source scoping (Left Pane), grounded copilot (Center Pane), and multi-format corporate document exporter (Right Pane) producing **Excel (`.xlsx`)**, **Word (`.docx`)**, **PowerPoint (`.pptx`)**, and **PDF (`.pdf`)** files.

## 2. Scope
1. **Multi-Format Document Exporters**:
   - `backend/app/services/reporting/excel_exporter.py` (`openpyxl`)
   - `backend/app/services/reporting/word_exporter.py` (`python-docx`)
   - `backend/app/services/reporting/powerpoint_exporter.py` (`python-pptx`)
   - `backend/app/services/reporting/pdf_exporter.py` (`reportlab`)
2. **API Endpoints**:
   - `POST /api/v1/agent/report/excel`
   - `POST /api/v1/agent/report/word`
   - `POST /api/v1/agent/report/powerpoint`
   - `POST /api/v1/agent/report/pdf`
3. **Frontend Studio Component**:
   - `frontend/src/components/NotebookLMStudio.tsx` with dynamic source checkboxes, real-time grounded SSE streaming, and instant artifact download buttons.
4. **Testing**:
   - `backend/tests/test_multiformat_export.py` with 4 unit tests.
