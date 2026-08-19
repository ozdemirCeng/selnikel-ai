# Selnikel AI — Architectural Decision Records (ADRs)

> **Context**: All major architectural and technical design decisions are recorded here. No architectural change may occur without authoring a new ADR or amending an existing record with rationale.

---

## ADR-001: PostgreSQL from Inception Instead of SQLite
- **Status**: ACCEPTED (2026-08-19)
- **Context**: While SQLite is simpler for standalone prototypes, Selnikel AI requires production-ready concurrency, robust indexing for SHA-256 deduplication, relational chunk relationships, and seamless multi-user transition.
- **Decision**: Use PostgreSQL 16 (via `asyncpg` and SQLAlchemy 2.0 async engine) from day one.
- **Consequences**: Zero database migration friction when transitioning from MVP to production V1. Docker Compose includes `postgres:16-alpine`.

---

## ADR-002: Encapsulation of Qdrant Behind Repository Pattern
- **Status**: ACCEPTED (2026-08-19)
- **Context**: Directly calling the Qdrant Python SDK from API endpoints or business services creates tight coupling to a specific vector database vendor.
- **Decision**: Implement [`QdrantVectorRepository`](file:///c:/Users/Diley/dev/workspace/selnikel-ai/backend/app/infrastructure/qdrant.py) inside `infrastructure/`, exposing pure domain entities (`DomainChunk`, `RetrievalResult`, `RetrievalFilter`).
- **Consequences**: The vector database implementation can be upgraded, mocked in tests, or replaced without touching domain or API layers.

---

## ADR-003: Provider-Agnostic LLM Abstraction with Local Air-Gapped Option
- **Status**: ACCEPTED (2026-08-19)
- **Context**: Sensitive Selnikel engineering documents (patents, boiler schematics, customer contracts) may eventually require 100% on-premise execution without external cloud egress.
- **Decision**: Create [`BaseLLMProvider`](file:///c:/Users/Diley/dev/workspace/selnikel-ai/backend/app/services/llm/base.py) with dynamic factory resolution (`OpenAIProvider` for cloud development, `OllamaProvider` for local open-source models).
- **Consequences**: Toggling between OpenAI and local Ollama is an environment variable configuration (`LLM_PROVIDER=openai` vs `LLM_PROVIDER=ollama`) requiring zero code changes.

---

## ADR-004: Decoupling Local Embeddings from LLM Provider
- **Status**: ACCEPTED (2026-08-19)
- **Context**: Many RAG systems tightly bind embeddings to the LLM vendor (e.g., using OpenAI embeddings when using GPT-4). This leaks private text during indexing even if the LLM is switched.
- **Decision**: Establish [`BaseEmbeddingProvider`](file:///c:/Users/Diley/dev/workspace/selnikel-ai/backend/app/services/embedding/base.py) as an independent service. Local multilingual `BAAI/bge-m3` is the baseline embedding standard for both Turkish and English engineering vocabularies.
- **Consequences**: Embeddings remain local and privacy-preserved regardless of whether the answer generation model is cloud-based or local.

---

## ADR-005: Decoupled Retrieval Contract for Shared Agent Tooling
- **Status**: ACCEPTED (2026-08-19)
- **Context**: The future AI Engineering Copilot will need tool functions like `search_documents()` and `get_document_page()`. Re-writing retrieval logic for agents creates code duplication and divergence.
- **Decision**: Implement [`BaseRetriever`](file:///c:/Users/Diley/dev/workspace/selnikel-ai/backend/app/services/retrieval/base.py) returning pure domain `RetrievalResult` objects. The deterministic RAG pipeline and future AI Agent tools invoke the exact same service method.
- **Consequences**: Seamless agent integration in V1 with zero rework of the retrieval pipeline.

---

## ADR-006: Clean Architecture & Domain Isolation from Frameworks
- **Status**: ACCEPTED (2026-08-19)
- **Context**: Heavy coupling to frameworks like LangChain or monolithic LlamaIndex pipelines leads to fragile codebases due to frequent breaking upstream API changes.
- **Decision**: Isolate core business models in `backend/app/domain/`. Use LlamaIndex or specialized libraries only as utility components (e.g., specific file readers or node splitters) behind domain abstractions.
- **Consequences**: High testability, zero vendor lock-in, and total control over prompt engineering, chunking, and retrieval logic.

---

## ADR-007: Mandatory Task Dossier & Adversarial Critic Protocol
- **Status**: ACCEPTED (2026-08-19)
- **Context**: LLM agents operating without structured records fall into ephemeral roleplay and repeat mistakes across sessions.
- **Decision**: Institute mandatory task dossiers (`tasks/TASK-XXX/`) and enforce that the developer who writes code cannot approve it. An independent critic must review and submit findings to the Engineering Manager.
- **Consequences**: Persistent institutional memory in Markdown files and verifiable quality gates before merging any feature.

---

## ADR-008: Platform Paradigm (NotebookLM 3-Pane Studio) & On-Premise Central Topology
- **Status**: ACCEPTED (2026-08-19)
- **Context**: Evaluated ChatGPT (single chat), Antigravity (IDE), and NotebookLM (grounded source studio). Industrial engineers require simultaneous side-by-side audit of dense technical tables, equipment catalogs, and page-level citations without installing heavy ML runtimes on individual office laptops.
- **Decision**:
  1. **Paradigm**: Adopt a **3-Pane Grounded Engineering Studio** (Left: Dossiers/Catalog, Center: Grounded SSE Chat with inline citations, Right: Live Source & Table Auditor).
  2. **Deployment Topology**: **Centralized On-Premise Intranet Server** (Docker Compose with PostgreSQL + Qdrant + Fast Central LLM/API) accessible to all factory engineers via web browser, with optional Tauri v2 desktop executable build from the exact same Next.js codebase.
- **Consequences**: Zero client install friction for engineers, instantaneous company-wide knowledge synchronization, 100% intellectual property protection (air-gappable), and maximum engineering table auditability.

---

## ADR-009: Obsidian AI Design System & Modern Engineering Craftsmanship
- **Status**: ACCEPTED (2026-08-19)
- **Context**: Default bootstrap and generic Tailwind styling fail modern ergonomics and visual quality standards required by top-tier engineering copilot tools.
- **Decision**: Implement the **Obsidian AI Design System** across the entire Next.js frontend:
  1. **Surface Ladder**: `#08090d` canvas with ambient radial mesh, `#0e111a` glassmorphic panels (`backdrop-blur-xl`), `#131722` elevated containers, and hairline borders (`border-white/[0.08]`).
  2. **Modern Engineering Typography & Semiotics**: High-contrast typography, electric cobalt-cyan luminescence, emerald verified citation tags, and amber calculation chips.
  3. **Sidebar Rail Navigation**: Collapsible Left Rail with quick switch tabs and real-time backend telemetry status.
- **Consequences**: Elevated world-class user experience comparable to Linear, Cursor, and Perplexity Pro.

---

## ADR-010: NotebookLM Workspace Paradigm & Multi-Format Industrial Exporters
- **Status**: ACCEPTED (2026-08-19)
- **Context**: Engineers need to transform grounded technical knowledge directly into standard engineering deliverables: Excel spreadsheets (`.xlsx`) for calculations, Word documents (`.docx`) for specifications, PowerPoint slides (`.pptx`) for presentations, and PDF reports (`.pdf`).
- **Decision**:
  1. Adopt the **NotebookLM 3-Pane Studio layout**: Left Sources checklist, Center grounded conversation, Right Artifact Studio.
  2. Implement native Python document export services using `openpyxl`, `python-docx`, `python-pptx`, and `reportlab`.
  3. Expose dedicated API endpoints `/api/v1/agent/export/{format}` (`excel`, `word`, `powerpoint`, `pdf`).
- **Consequences**: Engineers can generate complete corporate-formatted documents directly from the AI with zero manual copying.



