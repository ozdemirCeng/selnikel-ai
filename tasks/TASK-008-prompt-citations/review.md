# Review: TASK-008 — Grounded Industrial Prompt Design & Citation Formatting Engine

**Reviewer**: `RAG-02` (AI/RAG Critic)  
**Date**: 2026-08-19  
**Target Files**: `backend/app/services/rag/prompts.py`, `backend/app/services/rag/grounding.py`, `backend/tests/test_grounding.py`

---

## 1. Compliance Checklist
- [x] Acceptance Criteria strictly met without compromises
- [x] Zero-hallucination policy and exact refusal string embedded in system prompt
- [x] Explicit rule enforcing preservation of engineering units ($kg/h$, $bar$, $kW$, $^\circ C$)
- [x] Multi-format inline citation extraction (`[Belge: <name>, Sayfa: <page>]`)
- [x] Refusal edge cases return zero citations gracefully
- [x] Automated unit tests passing 100% (4/4 tests)

---

## 2. Detailed Findings & Audit Notes

### Finding 1: Context Isolation
- **Observation**: The context builder clearly isolates retrieved chunks with explicit metadata boundary markers (`--- [DOKÜMAN PARÇASI X] ---`).
- **Verification**: Verified via `test_build_rag_user_prompt_formats_context`.

### Finding 2: Unverified Citation Protection
- **Observation**: If an LLM creates an inline citation pointing to a page not in the retrieved set, it is marked as `unverified` and given a lower baseline score.
- **Verification**: Tested in `CitationEngine`.

---

## 3. Final Verdict
**VERDICT: PASS**  
Prompt design and citation extraction modules are certified production-ready.
