# Selnikel AI — Quality Gates & Verification Standards

> **Objective**: Define concrete, non-negotiable acceptance criteria, code review checklists, and testing standards required before any task may be transitioned to `COMPLETED`.

---

## 1. The Definition of "DONE"

A task is officially **DONE** when and only when all five gates are cleared:

$$\text{DONE} = \text{Research Artifact} + \text{Clean Implementation} + \text{Automated Tests} + \text{Independent Review (PASS)} + \text{State Reconciliation}$$

### Gate 1: Research Verification
- [ ] For any architectural or UI feature, a research document exists in `research/` or `tasks/<id>/research.md`.
- [ ] At least 3–5 real-world open-source references, production implementations, or official documentation sources are cited.
- [ ] Key architectural trade-offs, edge cases, and anti-patterns are documented.

### Gate 2: Implementation & Layer Discipline
- [ ] Domain models remain clean of framework/SDK dependencies (no direct Qdrant/FastAPI types in `domain/`).
- [ ] All database interactions occur through repositories or async sessions.
- [ ] All 9 chunk metadata fields and SHA-256 deduplication hashes are preserved.
- [ ] Pydantic v2 `ConfigDict` and strong typing are used throughout.
- [ ] Zero secrets, API keys, or raw hardcoded paths are committed.

### Gate 3: Automated Tests & Verification
- [ ] Unit tests written for new domain logic, utilities, and API endpoints.
- [ ] `pytest tests/` passes with **100% success** and **0 unhandled warnings**.
- [ ] Frontend builds with `npm run build` with **0 TypeScript and lint errors**.
- [ ] Runtime execution verified against running services.

### Gate 4: Independent Adversarial Review (PASS)
- [ ] A designated Critic (independent from the developer) reviews the implementation.
- [ ] The review follows the mandatory schema in `AGENTS.md` (Problem, Evidence, Impact, Required Fix).
- [ ] All P0/P1 blocking issues identified by the critic are resolved by the developer.
- [ ] The Critic issues an explicit **`VERDICT: PASS`** to the Engineering Manager.

### Gate 5: State Reconciliation & Task Dossier Archival
- [ ] `tasks/TASK-XXX/test-results.md` contains actual terminal logs and verification proof.
- [ ] `tasks/TASK-XXX/final.md` is signed off by the Engineering Manager.
- [ ] `PROJECT_STATE.md` and `agents/<division>/state.md` are updated to reflect the new ground truth.
- [ ] Task is moved from `tasks/active.md` to `tasks/completed.md`.

---

## 2. Reviewer Checklist by Division

### Backend & Infrastructure (`BE-02` / `ARC-02`)
- **Concurrency & Async**: Are database sessions properly closed? Are async calls awaited without blocking the event loop?
- **Data Integrity**: Are foreign keys, unique constraints (e.g. `(file_hash, version)`), and cascades correct?
- **Error Handling**: Are HTTP exceptions returned with structured error details instead of raw 500 stack traces?

### RAG & AI Pipeline (`RAG-02`)
- **Table Preservation**: Are tables in technical PDFs kept intact as single chunks?
- **Context Injection**: Does the system prompt strictly restrict the LLM to provided context?
- **Citation Attribution**: Are citations verified against retrieved chunk IDs and page numbers?
- **Token Budget**: Does the context window remain balanced without truncating vital technical tables?

### Frontend & UI/UX (`FE-02`)
- **Visual Hierarchy & Information Density**: Is the interface optimized for engineering workflows?
- **Edge States**: Are loading skeletons, error alerts, and empty states cleanly handled?
- **Citation Interactivity**: Can an engineer inspect the source document, page number, and chunk snippet?
- **Responsiveness**: Does the layout scale gracefully across desktop and mobile screens?
