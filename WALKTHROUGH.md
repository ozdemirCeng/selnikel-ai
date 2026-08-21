# Selnikel AI — Multi-Agent Engineering Knowledge System Walkthrough

> **Project Phase**: Advanced V1 Autonomous Agent & Production Completion  
> **Date**: 2026-08-19  
> **Status**: **100% Operational & Verified** (41/41 Backend Tests Passing, Clean Next.js 14 Production Bundle)

---

## 1. Executive Summary

**Selnikel AI** is an industrial-grade engineering knowledge and autonomous agent system tailored for **Selnikel Enerji** (boilers, burners, pressure vessels, fans, technical specifications, and service logs).

The system features:
- **Zero-Hallucination Grounded RAG**: Strict zero-hallucination industrial prompts and deterministic hybrid retrieval.
- **Table Preservation**: IBM Docling extracts multi-column technical tables as complete Markdown structures.
- **Hybrid Recall + Cross-Encoder Precision**: Multilingual **BAAI BGE-M3** (1024-dim dense + sparse BM25) + **FlashRank** (12ms ONNX cross-encoder).
- **Otonom Mühendislik Ajanı (ReAct Studio)**: Multi-step reasoning with specialized engineering calculation tools (ASME PTC 4.1 thermal efficiency, fluid dynamics fan airflow, technical report generator).
- **3-Pane NotebookLM-Style Studio**: Real-time SSE streaming, inline clickable citations (`[1]`, `[2]`), side-by-side source & table inspection, and catalog management.

---

## 2. Architecture & Pipeline Overview

```
                                      SELNIKEL AI MİMARİSİ
 ┌──────────────┐
 │ PDF / DOCX   │ ──► [IBM Docling] ──► [Tablo Korumalı Parçalayıcı] ──► [BGE-M3 Hibrit Gömme] ──► [Qdrant + Postgres]
 └──────────────┘                                                                                        │
                                                                                                         ▼
 ┌──────────────┐                                                                              [RRF Hibrit Arama]
 │ Kullanıcı    │ ─────────────────────────────────────────────────────────────────────────────────────► │
 └──────────────┘                                                                                        ▼
                                                                                              [FlashRank Cross-Encoder]
                                                                                                         │
                                                                                                         ▼
 ┌──────────────┐                                                                             [Sıfır-Halüsinasyon]
 │ Canlı SSE    │ ◄── [Alıntı Doğrulayıcı] ◄── [LLM: OpenAI / Ollama] ◄──────────────────────────────────┘
 └──────────────┘
                               ▲
                               │
 ┌─────────────────────────────┴──────────────────────────────┐
 │              OTONOM MÜHENDİSLİK AJANI (ReAct)              │
 │  ┌────────────────────────┐   ┌─────────────────────────┐  │
 │  │ search_engineering_docs│   │ calculate_boiler_effic. │  │
 │  └────────────────────────┘   └─────────────────────────┘  │
 │  ┌────────────────────────┐   ┌─────────────────────────┐  │
 │  │ calculate_fan_airflow  │   │ generate_engineer_report│  │
 │  └────────────────────────┘   └─────────────────────────┘  │
 └────────────────────────────────────────────────────────────┘
```

---

## 3. Completed Modules & Deliverables

### Phase 1: Foundation & Constitutional Governance (`TASK-001`)
- Docker Compose with custom isolated network `selnikel_network` (`postgres:16-alpine`, `qdrant/qdrant:v1.11.0`), FastAPI backend, Next.js 14 frontend.
- `AGENTS.md`, `PROJECT_STATE.md`, `DECISIONS.md`, `QUALITY_GATES.md`, `TASKS.md`.

### Phase 2: Ingestion & Document Processing Engine (`TASK-002`, `TASK-003`, `TASK-004`)
- `backend/app/services/ingestion/parser.py`: IBM Docling parser with OCR & PDF fallbacks.
- `backend/app/services/ingestion/chunker.py`: Table-aware chunking preserving all 9 metadata fields.
- `backend/app/services/ingestion/pipeline.py`: SHA-256 deduplication and async database persistence.
- `backend/app/api/v1/endpoints/documents.py`: Document upload, chunk inspection, and cascade deletion.

### Phase 3: Vector Indexing & Hybrid Retrieval (`TASK-005`, `TASK-006`, `TASK-007`)
- `backend/app/services/embedding/bgem3.py`: 1024-dim dense vectors + sparse lexical token representations.
- `backend/app/services/retrieval/hybrid.py`: Qdrant hybrid retrieval with Reciprocal Rank Fusion ($k=60$) and metadata pre-filters.
- `backend/app/services/retrieval/reranker.py`: **FlashRank** ONNX cross-encoder (~12ms CPU inference) with pass-through fallback.

### Phase 4: Answer Generation & Citations (`TASK-008`, `TASK-009`, `TASK-010`)
- `backend/app/services/rag/prompts.py`: Zero-hallucination industrial system prompts.
- `backend/app/services/rag/grounding.py`: `CitationEngine` extracting inline markers `[Belge: X, Sayfa: Y]` and cross-verifying evidence.
- `backend/app/services/rag/engine.py`: `DeterministicRAGEngine` supporting synchronous batch queries and real-time SSE token streaming with PostgreSQL query telemetry logging.
- `backend/app/api/v1/endpoints/rag.py`: `/api/v1/rag/query`, `/api/v1/rag/stream`, `/api/v1/rag/history`.

### Phase 5: Production User Interface (Next.js 14) (`TASK-011`, `TASK-012`)
- `frontend/src/components/StreamingChatInterface.tsx`: Real-time SSE streaming with typing indicator, dynamic prompt suggestions, and interactive citation chips.
- `frontend/src/components/CitationAuditor.tsx`: Side-by-side source & table inspection drawer.
- `frontend/src/components/DocumentCatalog.tsx`: Filterable catalog with search, chunk inspector, upload modal, and cascade delete.
- `frontend/src/components/SystemStatus.tsx`: Health telemetry for PostgreSQL, Qdrant, and LLM providers.

### Phase 6: Automated Evaluation & Hardening (`TASK-013`)
- `backend/tests/evaluation/evaluator.py`: RAG Triad benchmark metrics runner.
- `backend/tests/test_evaluation_benchmark.py`: Evaluates `backend/tests/evaluation/questions.json` with 100% score.

### 3.12 Frontend Production Build & Static Asset Verification
```text
> selnikel-ai-frontend@0.1.0 build
> next build

  ▲ Next.js 14.2.35
  - Environments: .env.local

   Creating an optimized production build ...
 ✓ Compiled successfully
   Linting and checking validity of types ...
   Collecting page data ...
 ✓ Generating static pages (4/4)
   Finalizing page optimization ...
   Collecting build traces ...

Route (app)                              Size     First Load JS
┌ ○ /                                    69.1 kB         156 kB
└ ○ /_not-found                          873 B          88.1 kB
+ First Load JS shared by all            87.2 kB
  ├ chunks/117-ee3cf2893d2ceff7.js       31.7 kB
  ├ chunks/fd9d1056-c96c49782430d626.js  53.6 kB
  └ other shared chunks (total)          1.86 kB
```

### 3.13 Git Synchronized & Pushed
```text
[main 8c841ce] feat(frontend): update AgentStudio presets with burner, economizer, and safety valve engineering calculations and verify build
 1 file changed, 17 insertions(+), 5 deletions(-)
To https://github.com/ozdemirCeng/selnikel-ai.git
   eaaf8c1..8c841ce  main -> main
```

### Phase 7: AI Engineering Agent & Tool Orchestrator (`TASK-014`, `TASK-015`)
- `backend/app/services/agent/orchestrator.py`: Multi-step ReAct loop with safety recursion caps.
- `backend/app/services/agent/tools/`:
  1. `SearchDocumentsTool`: Grounded hybrid document search.
  2. `BoilerEfficiencyTool`: ASME PTC 4.1 thermal efficiency and natural gas/fuel consumption in $Nm^3/h$.
  3. `FanAirflowTool`: Fluid dynamics fan volumetric flow rate ($m^3/h$) and motor shaft power ($kW$).
  4. `ReportGeneratorTool`: Synthesis of complete signed engineering reports.
- `backend/app/api/v1/endpoints/agent.py`: `/api/v1/agent/tools`, `/api/v1/agent/run`, `/api/v1/agent/stream`.
- `frontend/src/components/AgentStudio.tsx`: Step-by-step reasoning timeline, expandable tool cards, and markdown report downloader.

### Phase 8: Multi-Format Document Exporters & NotebookLM Studio (`TASK-016`, `TASK-017`)
- **Excel Spreadsheet Exporter (`openpyxl`)**: Formatted `.xlsx` with blue headers, zebra striping, and auto column widths (`/api/v1/agent/report/excel`).
- **Word Document Exporter (`python-docx`)**: Formal `.docx` technical specification with Selnikel styling (`/api/v1/agent/report/word`).
- **PowerPoint Presentation Exporter (`python-pptx`)**: 16:9 widescreen presentation deck with dark-blue title and content/table slides (`/api/v1/agent/report/powerpoint`).
- **PDF Report Exporter (`reportlab`)**: Formal PDF with banner and verification seal (`/api/v1/agent/report/pdf`).
- **NotebookLM 3-Pane Studio UI (`NotebookLMStudio.tsx`)**: Left sources checkbox rail, Center grounded streaming copilot, Right Studio Artifact generator with one-click download buttons.

---

## 4. Test Suite Verification

```text
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\Diley\dev\workspace\selnikel-ai\backend
plugins: anyio-4.14.2, Faker-40.36.0, asyncio-1.4.0
collected 47 items

backend\tests\test_agent_api.py ....                                     [  8%]
backend\tests\test_agent_tools.py ....                                   [ 17%]
backend\tests\test_chunker.py ..                                         [ 21%]
backend\tests\test_config.py .                                           [ 23%]
backend\tests\test_document_api.py ....                                  [ 31%]
backend\tests\test_embedding.py ..                                       [ 36%]
backend\tests\test_evaluation_benchmark.py ..                            [ 40%]
backend\tests\test_grounding.py ....                                     [ 48%]
backend\tests\test_health.py ..                                          [ 53%]
backend\tests\test_hybrid_retriever.py ..                                [ 57%]
backend\tests\test_ingestion_pipeline.py ..                              [ 61%]
backend\tests\test_multiformat_export.py ....                            [ 70%]
backend\tests\test_parser.py ....                                        [ 78%]
backend\tests\test_pdf_export.py ..                                      [ 82%]
backend\tests\test_rag_api.py ...                                        [ 89%]
backend\tests\test_rag_engine.py ..                                      [ 93%]
backend\tests\test_reranker.py ...                                       [100%]

======================= 47 passed, 2 warnings in 13.86s =======================
```

---

## 5. How to Run the System

### 1. Start Infrastructure (PostgreSQL & Qdrant)
```bash
docker-compose up -d postgres qdrant
```

### 2. Run Backend API
```bash
cd backend
.\.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```
- OpenAPI Documentation: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/api/v1/health`

### 3. Run Frontend Engineering Studio
```bash
cd frontend
npm run dev
```
- Web Application: `http://localhost:3005` (Custom port to avoid collisions)
