# Task Brief: TASK-008 — Grounded Industrial Prompt Design & Citation Formatting Engine

## 1. Goal
Design engineering system prompts enforcing zero-hallucination policies and implement a post-generation citation extraction and verification engine that maps claims to exact document filenames, page numbers, and snippet evidence.

## 2. Scope
1. **Mandatory Research (`research.md`)**:
   - Prompt engineering patterns for high-precision industrial RAG (strict grounding, explicit refusal on missing info, unit preservation).
   - Inline citation attribution formats: `[Belge: <name>, Sayfa: <page>, Bölüm: <section>]`.
   - Post-generation citation parser & verification against retrieved chunks.
2. **Implementation**:
   - `backend/app/services/rag/prompts.py`: Industrial system prompts, context block builder with numbered source labels.
   - `backend/app/services/rag/grounding.py`: `CitationEngine` to extract citations, verify document existence, and construct structured `Citation` domain models.
3. **Automated Testing & Adversarial Review**:
   - Unit tests in `backend/tests/test_grounding.py`.
   - Adversarial review by `RAG-02`.

## 3. Acceptance Criteria
- [ ] Research artifact authored detailing industrial grounding patterns.
- [ ] System prompt enforces strict context adherence and explicit refusal when context is missing.
- [ ] `CitationEngine` parses inline citations and maps to `Citation` domain objects.
- [ ] Unit tests pass with 100% success.
- [ ] Adversarial review completed by `RAG-02` with `VERDICT: PASS`.
