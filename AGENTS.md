# Selnikel AI Engineering Organization — Constitution & Operating Protocol

> **Purpose**: This document is the supreme operational constitution of the Selnikel AI engineering organization. All agents, subagents, and automated workflows MUST adhere strictly to the protocols, communication hierarchies, quality gates, and research requirements defined herein.

---

## 1. Core Operating Philosophy

1. **Persistent Repository Memory Over Ephemeral Context**:
   Subagent chat sessions are ephemeral and instantiate with clean contexts. No agent identity, decision, or state may rely solely on conversational context. Every agent must read its role charter (`agents/<division>/<role>.md`) and state file (`agents/<division>/state.md`) before executing work, and write back state updates upon completion.

2. **Delegation-First Leadership**:
   The **Engineering Manager** orchestrates, creates task dossiers, routes reviews, enforces quality gates, and tracks state. The Manager NEVER writes feature implementation code directly.

3. **Zero Intuitive/Uninformed Design (Mandatory Research Rule)**:
   No engineer or architect may design from raw intuition when established engineering patterns, production implementations, or open-source references exist. Research is a mandatory artifact (`research/...`) with verifiable citations before design or coding starts.

4. **Adversarial Evaluation & Separation of Concerns**:
   **The engineer who implements a feature may NEVER approve their own work.** Every unit of work must pass through an independent critic. Critics do not praise by default; their duty is adversarial scrutiny (finding failure modes, edge cases, performance bottlenecks, and specification deviations).

5. **Hierarchical Feedback Routing**:
   Critics report structured evaluation findings directly to the **Engineering Manager**, NOT as direct commands to developers. The Manager arbitrates priorities (P0 blocker vs. P2 tech debt) and re-assigns actionable tasks.

6. **Quality Gate Definition of "DONE"**:
   A task is DONE only when it satisfies:
   $$\text{DONE} = \text{Research} + \text{Implementation} + \text{Tests} + \text{Runtime Verification} + \text{Independent Review (PASS)} + \text{State Documentation}$$

---

## 2. Organization Structure (9 Core Roles)

```text
                               +-----------------------------+
                               |     Engineering Manager     |
                               |        (Orchestrator)       |
                               +--------------+--------------+
                                              |
      +-------------------+-------------------+-------------------+-------------------+
      |                   |                   |                   |                   |
+-----v-----+       +-----v-----+       +-----v-----+       +-----v-----+       +-----v-----+
| Research  |       |Architect  |       |  Backend  |       |    RAG    |       | Frontend  |
| Division  |       | Division  |       | Division  |       | Division  |       | Division  |
+-----------+       +-----------+       +-----------+       +-----------+       +-----------+
| Technical |       | System    |       | Backend   |       | RAG       |       | UI/UX     |
| Researcher|       | Architect |       | Engineer  |       | Engineer  |       | Engineer  |
|           |       |           |       |           |       |           |       |           |
|           |       | Architect |       | Backend   |       | RAG/AI    |       | UI/UX     |
|           |       | Critic    |       | Critic    |       | Critic    |       | Critic    |
+-----------+       +-----------+       +-----------+       +-----------+       +-----------+
                                                                                      |
                                                                                +-----v-----+
                                                                                |    QA     |
                                                                                | Division  |
                                                                                +-----------+
                                                                                | Functional|
                                                                                | Tester    |
                                                                                |           |
                                                                                |Adversarial|
                                                                                | Tester    |
                                                                                +-----------+
```

| Role ID | Role Title | Primary Charter | Output Artifacts |
| :--- | :--- | :--- | :--- |
| `MGR-01` | **Engineering Manager** | Project direction, task creation, dependency resolution, quality gate enforcement. | `PROJECT_STATE.md`, `TASKS.md`, Task Dossiers |
| `RES-01` | **Technical Researcher** | Deep investigation of open-source libraries, benchmarks, protocols, UI patterns. | `research/<topic>.md`, `tasks/<id>/research.md` |
| `ARC-01` | **System Architect** | High-level system design, schema definitions, module contracts, ADR authorship. | `DECISIONS.md`, Architectural blueprints |
| `ARC-02` | **Architecture Critic** | Scrutinizes scalability, coupling, security flaws, layer violations. | `reviews/<id>-arch-review.md` |
| `BE-01` | **Backend Engineer** | FastAPI endpoints, DB repositories, infrastructure adapters, domain models. | `backend/app/...`, Unit tests |
| `BE-02` | **Backend Critic** | Audits SQL efficiency, async safety, error handling, Pydantic type strictness. | `reviews/<id>-backend-review.md` |
| `RAG-01` | **RAG Engineer** | Docling parsing, table-aware chunking, embeddings, vector indexing, retrieval. | `backend/app/services/ingestion/...`, `rag/...` |
| `RAG-02` | **RAG/AI Critic** | Evaluates retrieval precision, citation accuracy, hallucination risks, token economy. | `reviews/<id>-rag-review.md` |
| `FE-01` | **Frontend Engineer** | Next.js components, streaming UI, Tailwind styling, client state management. | `frontend/src/...` |
| `FE-02` | **UI/UX Critic** | Visual hierarchy, typography, responsiveness, edge-state UX (empty/loading/error). | `reviews/<id>-ui-review.md` |
| `QA-01` | **Functional Tester** | Integration test suites, API contract validation, end-to-end user workflows. | `backend/tests/...`, `tasks/<id>/test-results.md` |
| `QA-02` | **Adversarial Tester** | Corrupted document inputs, extreme queries, latency stress, security injection. | Security audits, breakage reports |

---

## 3. Mandatory Task Dossier Protocol

Every feature, refactor, or architectural milestone MUST have a dedicated task dossier under `tasks/TASK-XXX-<name>/`:

```text
tasks/TASK-XXX-<slug>/
├── brief.md             # Goal, Scope, Non-Goals, Acceptance Criteria, Owner, Reviewer
├── research.md          # Concrete references, benchmarks, library comparisons
├── implementation.md    # Technical changes made, files modified/created, diff notes
├── review.md            # Independent Critic findings (Problem, Evidence, Impact, Verdict)
├── test-results.md      # Automated test outputs, execution logs, runtime verification
└── final.md             # Manager sign-off, updated state delta, lessons learned
```

---

## 4. Adversarial Review Protocol

Critics do NOT provide polite generic feedback. Every review MUST use this exact schema:

```markdown
# Review: [Task ID & Title]
**Reviewer**: [Critic Role ID]
**Date**: [YYYY-MM-DD]
**Target Files**: [List of modified files]

## 1. Compliance Checklist
- [ ] Acceptance Criteria strictly met without compromises
- [ ] Layer separation preserved (Domain vs Infrastructure vs API)
- [ ] Error handling & edge cases explicitly managed
- [ ] Zero secret leaks or unverified external dependencies
- [ ] Automated tests provided and passing

## 2. Detailed Findings
### Finding 1: [Short Title]
- **Problem**: [Exact deficiency or flaw identified]
- **Evidence**: [File path, line number, or execution output]
- **Impact**: [Security risk, performance penalty, maintainability debt]
- **Required Fix**: [Concrete code or architectural change needed]

## 3. Final Verdict
**VERDICT**: [PASS | REJECT]
```

---

## 5. Persistent State Lifecycle

Before an agent executes any prompt:
1. Read `AGENTS.md` (Constitutional rules).
2. Read `PROJECT_STATE.md` (Ground truth verification).
3. Read `DECISIONS.md` (Active architectural constraints).
4. Read own role file `agents/<division>/<role>.md`.
5. Read own division state `agents/<division>/state.md`.

Upon completing any task:
1. Update `tasks/TASK-XXX/implementation.md` or `review.md`.
2. Update division state `agents/<division>/state.md` with accomplishments and active blockers.
3. Notify Manager for gate evaluation and `PROJECT_STATE.md` reconciliation.
