# Task Brief: TASK-001 — Engineering Organization & Foundation Bootstrap

## 1. Goal
Establish a robust, modular, and production-ready foundation for Selnikel AI, including Docker Compose, PostgreSQL 16 metadata models, Qdrant repository wrapper, provider-agnostic LLM interface, FastAPI application skeleton, Next.js frontend skeleton, evaluation QA dataset, and multi-agent governance memory files.

## 2. Scope
- Container orchestration (PostgreSQL, Qdrant, Backend, Frontend).
- FastAPI backend with clean architecture layers (`domain`, `infrastructure`, `services`, `api`, `schemas`).
- PostgreSQL schema for `documents`, `document_chunks` (9 metadata fields preserved), and `query_logs`.
- Qdrant repository abstraction encapsulating vector database access.
- Provider-agnostic LLM interface supporting OpenAI and Ollama.
- Next.js 14 frontend with live system status component.
- Unit testing harness and evaluation benchmark QA dataset.
- Multi-agent constitution (`AGENTS.md`), project ground truth (`PROJECT_STATE.md`), decisions (`DECISIONS.md`), and quality gates (`QUALITY_GATES.md`).

## 3. Non-Goals
- Full Docling ingestion pipeline (deferred to Phase 2).
- Vector retrieval and chunking implementation (deferred to Phase 3).
- Autonomous agent tools or interactive chat (deferred to later phases).

## 4. Acceptance Criteria
- [x] Docker Compose file created and configured.
- [x] PostgreSQL 16 models created preserving all 9 chunk metadata fields + SHA-256 hash.
- [x] Qdrant client wrapped behind repository interface.
- [x] BaseLLMProvider implemented with OpenAI and Ollama providers.
- [x] FastAPI `/api/v1/health` endpoint returning component latencies.
- [x] Next.js builds with zero TypeScript errors and renders live status component.
- [x] Unit tests pass with 100% success.
- [x] Zero secrets or sensitive credentials committed.
