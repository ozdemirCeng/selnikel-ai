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

## ADR-010: Native Multi-Format Industrial Exporters (Excel, Word, PDF)
- **Status**: ACCEPTED (2026-08-19)
- **Context**: Engineers need to transform grounded technical knowledge directly into standard engineering deliverables: Excel spreadsheets (`.xlsx`) for calculations, Word documents (`.docx`) for specifications, and PDF reports (`.pdf`).
- **Decision**:
  1. Implement native Python document export services using `openpyxl`, `python-docx`, and `reportlab`.
  2. Expose dedicated API endpoints `/api/v1/agent/export/{format}` (`excel`, `word`, `pdf`).
- **Consequences**: Engineers can generate complete corporate-formatted documents directly from the AI with zero manual copying.

---

## ADR-011: OIDC Authentication Architecture — Backend-For-Frontend (BFF) Pattern
- **Status**: ACCEPTED (2026-08-19)
- **Context**: Evaluating SPA Direct Entra ID token handling vs. Backend-for-Frontend (BFF) pattern. Exposing raw bearer tokens in browser memory (`localStorage` / JS runtime) creates XSS token exfiltration risks for enterprise blueprints.
- **Decision**: Adopt the **BFF (Backend-For-Frontend)** architecture:
  1. The backend coordinates OIDC token exchanges with Microsoft Entra ID / IdP.
  2. Session tokens are issued to the browser exclusively as `HttpOnly`, `Secure`, `SameSite=Strict` cookies.
  3. All REST and SSE streaming endpoints authenticate via cookie or standard Authorization header for machine clients.
- **Consequences**: Maximum browser-level credential security, zero custom token generator sprawl, and native CSRF double-submit protection.

---

## ADR-012: PostgreSQL-Native Task Queue via `SELECT FOR UPDATE SKIP LOCKED`
- **Status**: ACCEPTED (2026-08-19)
- **Context**: Evaluating Celery/Redis vs. PostgreSQL-native asynchronous job queues for long-running document ingestion (Docling OCR, chunking, embedding).
- **Decision**: Implement a **PostgreSQL-native worker queue** using `SELECT ... FOR UPDATE SKIP LOCKED`:
  1. Ingestion jobs are tracked in the `ingestion_jobs` table with states (`queued`, `validating`, `parsing`, `chunking`, `embedding`, `indexing`, `verifying`, `completed`, `failed`).
  2. Workers run as independent Python background processes with worker lease timeouts (heartbeats), exponential backoff, and dead-letter states.
- **Consequences**: Eliminates Redis/RabbitMQ infrastructure overhead in pilot deployments while guaranteeing ACID transactional durability and exactly-once processing.

---

## ADR-013: Hybrid Storage Adapter — Local Encrypted Volume with S3 Protocol Readiness
- **Status**: ACCEPTED (2026-08-19)
- **Context**: Industrial installations may run fully air-gapped on factory on-premise hardware without AWS S3 or MinIO object storage.
- **Decision**: Implement a storage abstraction (`BaseStorageAdapter`) with:
  1. `LocalStorageAdapter`: Stores content-addressed binaries at `storage/{sha256[:2]}/{sha256}.bin` with path-traversal sanitization.
  2. `S3StorageAdapter`: Ready for MinIO or AWS S3 object buckets.
  3. Pre-upload Magic-Byte MIME verification and 50 MB hard size limit.
- **Consequences**: Zero friction between air-gapped on-premise single-server setups and multi-node cloud deployments.

---

## ADR-014: Triple-Layer Access Control (ACL) & Cache Partitioning
- **Status**: ACCEPTED (2026-08-19)
- **Context**: Ensuring sensitive Ar-Ge patents or confidential cost sheets never leak across departments or through semantic response caches.
- **Decision**: Enforce ACL simultaneously across **3 distinct architectural layers**:
  1. **Layer 1 (PostgreSQL)**: SQL queries filter by user's assigned `department_ids` and roles.
  2. **Layer 2 (Qdrant Vector)**: Vector queries inject mandatory payload filters (`metadata.department_id in user.departments`).
  3. **Layer 3 (Answer Provenance)**: The RAG engine re-verifies every candidate citation against the active user ACL before rendering the final response.
  4. **Cache Partitioning**: RAG response cache keys strictly include `(user_id, department_ids, classification, acl_version)`.
- **Consequences**: Absolute data isolation with zero cross-department cache contamination.

---

## ADR-015: Three Distinct Deployment Profiles (`cloud-enabled`, `local-private`, `air-gapped`)
- **Status**: ACCEPTED (2026-08-19)
- **Context**: Different Selnikel operating environments have varying internet connectivity and security classification constraints.
- **Decision**: Explicitly define and enforce 3 deployment profiles via `DEPLOYMENT_PROFILE` environment variable:
  1. `cloud-enabled`: Allows external OpenAI/Azure LLMs for public data.
  2. `local-private`: Uses local Ollama/vLLM models while allowing outbound telemetry and package updates.
  3. `air-gapped`: 100% offline, local BGE-M3, local FlashRank, local Ollama (Qwen2.5-14B), local fonts, zero external HTTP egress, pre-packaged weights.
- **Consequences**: Total regulatory and intellectual property compliance for defense and sensitive industrial clients.

---

## ADR-016: Soft Delete, 90-Day Retention, and Append-Only Audit Integrity
- **Status**: ACCEPTED (2026-08-19)
- **Context**: Industrial compliance (ISO 9001, CE, ASME) requires non-repudiation and tracking who viewed or modified engineering specifications.
- **Decision**:
  1. **Soft Delete**: All documents and revisions use `deleted_at: timestamptz`. Physical deletion requires a two-man rule (`admin` + `approver`).
  2. **Retention**: Soft-deleted records are retained for 90 days before cold archival.
  3. **Append-Only Audit Log**: The `audit_events` table is append-only; database updates/deletes on this table are revoked at the SQL grant level.
- **Consequences**: Full compliance with ISO quality audits and legal non-repudiation.

---

## ADR-017: UUID v4 Standard for All Primary Identifiers
- **Status**: ACCEPTED (2026-08-19)
- **Context**: Sequential integer IDs leak business intelligence (e.g. document count) and complicate distributed multi-site replication.
- **Decision**: Standardize on RFC 4122 `UUID v4` for all primary keys across PostgreSQL, Qdrant payload IDs, and API DTOs.
- **Consequences**: Secure, collision-free, distributed-ready identifiers across all services.

---

## ADR-018: Cursor-Based API Pagination Standard
- **Status**: ACCEPTED (2026-08-19)
- **Context**: Offset-based pagination (`OFFSET 1000`) exhibits poor query performance on large chunk tables and suffers from page-drift anomalies during real-time document ingestion.
- **Decision**: Standardize all collection endpoints (`/documents`, `/equipment`, `/audit/events`) on **cursor-based pagination** with opaque cursor tokens (`limit`, `next_cursor`, `prev_cursor`).
- **Consequences**: Sub-millisecond pagination performance and stable iteration during concurrent document indexing.

---

## ADR-019: Document Revision Immutability & Supersedes Graph
- **Status**: ACCEPTED (2026-08-19)
- **Context**: Engineering specifications must maintain strict version history. Editing an approved specification directly destroys traceability.
- **Decision**:
  1. A `DocumentRevision` is **immutable** once approved (`approval_status = 'approved'`).
  2. Any changes spawn a new `DocumentRevision` with `supersedes_revision_id` pointing to the prior revision.
  3. Queries default to `revision_policy: approved_latest`.
- **Consequences**: Guaranteed historical accuracy and instant visual diff generation between revisions.

---

## ADR-020: Spatial FastFallbackParser, Dynamic Table Grid Clustered Boundaries, and Optional AI Document Converters

- **Date**: 2026-08-20
- **Status**: PROPOSED (SUBMITTED FOR MANAGER REVIEW)
- **Context**: Document ingestion in Selnikel AI requires both high fidelity across complex layouts (multi-column PDF tables, multi-page DOCX documents) and guaranteed determinism in lightweight CI, testing, and offline environments where heavy OCR (Tesseract), Poppler rendering binaries, or Docling dependencies are unavailable or cost-prohibitive.
- **Decision**:
  1. Implement a spatial, coordinate-based fallback parser (`FastFallbackParser`) using `pypdf` spatial visitor geometry (`visitor_text`) and `python-docx` element-order traversal as the baseline deterministic parser.
  2. Implement strict table-grid detection with spatial clustering:
     - Group text elements by Y-coordinate ($\pm 3.0\text{ pt}$) into candidate lines.
     - Isolate section headers from tabular data blocks using full-line equality (never substring containment that drops valid short cells like `"A"`, `"B"`, `"C"`).
     - Cluster multi-column lines using vertical proximity ($\Delta y \le 35.0\text{ pt}$) to properly separate distinct tables on the same page.
     - Require identical column counts ($K = \text{len(hdr)}$) across all data rows in a table block.
     - Disallow model codes (`SB-5000`) or plain text from acting as table captions or section headings.
  3. Traverse DOCX elements in native XML body sequence (`w:p`, `w:tbl`) with explicit page-break detection (`w:br[w:type="page"]`) and pipe character escaping (`\|`).
  4. Decouple IBM Docling and Tesseract OCR into optional runtime converter plugins. When external binaries or packages are absent, `DocumentParserFactory` transparently routes documents to `FastFallbackParser` and explicitly records `ocr_applied: false` in document metadata.
- **Alternatives Considered**:
  - Hard requirement on Docling/Tesseract binaries in all environments (Rejected: Fails in standard Python lightweight CI and offline developer workstations).
  - Simple flat-text PDF extraction without spatial coordinates (Rejected: Loses all multi-column table layout fidelity).
- **Reason**: Guarantees zero-dependency reproducible baseline execution while maintaining structural table fidelity and clear operational telemetry.
- **Consequences**: Fast fallback parsing runs identically across Windows, Linux, and macOS without external OS packages. OCR state is explicitly declared in all ingestion payloads.
