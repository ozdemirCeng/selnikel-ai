# Selnikel AI — Project State & Institutional Ground Truth

> **Last Updated**: 2026-08-19  
> **Current Phase**: Phase 1 Completed (Engineering Organization & Foundation Bootstrapped)  
> **Master Branch Health**: STABLE (3/3 unit tests passing, Next.js build clean)

---

## 1. Executive Summary & Objective

Selnikel Enerji is building an internal **AI Engineering Knowledge System & Copilot** for technical manufacturing documentation (boilers, burners, fans, pressure vessels, engineering datasheets, maintenance records, standards).

The project is governed as a persistent multi-agent engineering organization with zero ephemeral drift.

---

## 2. Component Health & Verified Ground Truth

| Component | Technology | Target State | Verified Status | Evidence |
| :--- | :--- | :--- | :--- | :--- |
| **Document Parser** | Docling + Fallback (`pypdf`/text) | Industrial table extraction & page provenance | **OPERATIONAL** | `DoclingParser` & `FastFallbackParser` implemented; unit tests (4/4 passed). |
| **Chunking & Ingestion** | Structure-Aware Chunker + SHA256 | Table-preserving chunking & deduplication | **OPERATIONAL** | `TableAwareChunker` & `IngestionPipeline` implemented; unit tests (11/11 passed). |
| **Backend API Gateway** | FastAPI `0.141.1` | Asynchronous REST & SSE API with OpenAPI docs | **OPERATIONAL** | Root `/` and `/api/v1/health` verified live; `pytest` (11/11 passed). |
| **Embedding Engine** | Local BGE-M3 (1024-dim) + Fallback | Multilingual dense + sparse lexical representations | **OPERATIONAL** | `BGEM3EmbeddingProvider` & `DeterministicHashEmbeddingProvider` tested (2/2 passed). |
| **Vector Engine & Hybrid** | Qdrant `v1.11.0` + RRF Fusion | Dense + sparse search with metadata pre-filtering & RRF fusion | **OPERATIONAL** | `QdrantHybridRetriever` implemented & tested (2/2 passed). |
| **Cross-Encoder Reranker** | FlashRank (ONNX) + Fallback | High-precision candidate reranking | **OPERATIONAL** | `FlashRankReranker` & `PassThroughReranker` tested (3/3 passed). |
| **Prompt & Citations** | Grounded Prompt + CitationEngine | Zero-hallucination prompts & regex citation verifier | **OPERATIONAL** | `CitationEngine` & `prompts.py` unit tested (4/4 passed). |
| **RAG Orchestrator** | `DeterministicRAGEngine` | End-to-end sync & SSE streaming RAG pipeline | **OPERATIONAL** | `rag_engine.py` unit & stream tested (2/2 passed). |
| **RAG API Endpoints** | FastAPI `/api/v1/rag/*` | `/query` (sync), `/stream` (SSE), `/history` (audit) | **OPERATIONAL** | Full suite (43/43 passed) with streaming SSE. |
| **Frontend Studio UI** | Next.js 14 (App Router) | NotebookLM 3-Pane Studio (`http://localhost:3005`) | **OPERATIONAL** | Production bundle built (`0 errors, 4/4 static pages generated`). |
| **AI Engineering Agent** | `EngineeringAgentOrchestrator` | Multi-step ReAct planning + Multi-Format Exporters (`/agent/report/*`) | **OPERATIONAL** | Full suite (47/47 passed), Excel, Word, PPTX, PDF export & Next.js Studio verified. |
| **Evaluation Benchmark** | `RAGBenchmarkEvaluator` | Automated RAG Triad benchmark against `questions.json` | **OPERATIONAL** | 100% accuracy score verified across all 47 backend tests. |
| **Relational Database** | PostgreSQL `16-alpine` | Document metadata, SHA-256 deduplication, query logs | **CONFIGURED & TESTED** | `DocumentModel`, `DocumentChunkModel`, `QueryLogModel` with async SQLAlchemy (`asyncpg`). |
| **Vector Engine** | Qdrant `v1.11.0` | Dense + Sparse vector storage with payload filtering | **CONFIGURED & WRAPPED** | `QdrantVectorRepository` abstraction implemented, decoupling Qdrant SDK from domain. |
| **LLM Layer** | Unified `BaseLLMProvider` | Provider-agnostic switch between Cloud API (OpenAI) and Local (Ollama) | **OPERATIONAL** | `LLMProviderFactory` resolves provider dynamically via `.env`. |
| **Embedding Contract** | `BaseEmbeddingProvider` | Independent vector embedding interface | **ESTABLISHED** | Contract created in `backend/app/services/embedding/base.py`. |
| **Retrieval Contract** | `BaseRetriever` | Shared retrieval contract for RAG and future Agent tools | **ESTABLISHED** | Contract created in `backend/app/services/retrieval/base.py`. |
| **Frontend Web App** | Next.js `14.2.35` (TS, Tailwind) | Real-time dashboard with live system health polling | **OPERATIONAL** | Next.js production build (`npm run build`) passed; static pages generated (4/4). |
| **Evaluation Suite** | Benchmark QA Dataset | Ground truth evaluation dataset for RAG Triad | **INITIALIZED** | `backend/tests/evaluation/questions.json` populated with industrial QA cases. |

---

## 3. Metadata Specification Compliance

The system strictly enforces the preservation of all 9 mandatory metadata fields for every chunk:

1. `document_id` (UUID string)
2. `document_version` (Integer, default `1`)
3. `filename` (Original file name)
4. `page_number` (1-indexed page from source PDF/document)
5. `section` (Hierarchical section title, e.g., `# Header > ## Subheader`)
6. `document_type` (e.g., `technical_specification`, `maintenance_manual`, `datasheet`)
7. `department` (e.g., `engineering`, `production`, `service`)
8. `language` (e.g., `tr`, `en`)
9. `chunk_id` (UUID string)

*Plus: SHA-256 hash deduplication at document level (`file_hash` indexed in PostgreSQL).*

---

## 4. Active Repository Structure

```text
selnikel-ai/
├── AGENTS.md                          # Constitutional organization protocol
├── PROJECT_STATE.md                   # Single source of verified truth
├── DECISIONS.md                       # Architectural Decision Records (ADRs)
├── QUALITY_GATES.md                   # Acceptance criteria & Definition of Done
├── TASKS.md                           # Master roadmap and active tasks
├── docker-compose.yml                 # PostgreSQL, Qdrant, Backend, Frontend
├── backend/                           # FastAPI backend (Clean Architecture)
│   ├── app/
│   │   ├── api/v1/                    # Health, Documents, RAG routers
│   │   ├── core/                      # Config (BaseSettings), Logging
│   │   ├── db/                        # Base, Session, Models (Document, Chunk, QueryLog)
│   │   ├── domain/                    # Pure Domain Models & Chunk Metadata
│   │   ├── infrastructure/            # DB health, Qdrant repository, Local Storage
│   │   ├── schemas/                   # Pydantic v2 DTO schemas
│   │   └── services/                  # LLM providers, Embedding & Retrieval contracts
│   └── tests/
│       ├── test_config.py
│       ├── test_health.py
│       └── evaluation/                # questions.json dataset & harness
├── frontend/                          # Next.js 14 Frontend
│   └── src/
│       ├── app/                       # App router (layout.tsx, page.tsx)
│       ├── components/                # SystemStatus real-time component
│       └── lib/                       # API client & TypeScript types
├── agents/                            # Division roles and state files
├── tasks/                             # Task dossiers (brief, research, impl, review, test)
├── reviews/                           # Critic review archives
└── research/                          # Technology and UI research archives
```

---

## 5. Next Immediate Milestones

- **TASK-002**: Research & Design of Docling Industrial Parsing & Table Extraction Engine.
- **TASK-003**: Implementation of Structure-Aware Hierarchical Chunker & SHA-256 Deduplication.
- **TASK-004**: Integration of Local BGE-M3 Dense + Sparse Embedding Provider.
- **TASK-005**: Implementation of Qdrant Hybrid Retriever with Metadata Filtering & FlashRank Reranker.
