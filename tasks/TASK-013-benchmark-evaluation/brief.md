# Task Brief: TASK-013 — Automated Benchmark Evaluation Pipeline against questions.json

## 1. Goal
Implement an automated, objective evaluation benchmark that runs test questions from `backend/tests/evaluation/questions.json` through the deterministic RAG pipeline, measuring Context Relevance, Citation Precision, and Keyword/Parameter Recall to verify zero-hallucination accuracy.

## 2. Scope
1. **Evaluation Engine (`backend/tests/evaluation/evaluator.py`)**:
   - Loads evaluation questions dataset.
   - Computes:
     - `Context Relevance`: Correct document filename and page number retrieved.
     - `Citation Precision`: Citations match ground truth evidence.
     - `Keyword/Parameter Recall`: Critical engineering values (e.g. 16 bar, 500 hours, EN 12953) present in answer.
     - `Overall RAG Score`: Weighted composite metric.
2. **Automated Test (`backend/tests/test_evaluation_benchmark.py`)**:
   - Runs full benchmark assertions.
3. **Acceptance Criteria**:
   - [ ] Automated evaluation runner evaluates all questions in `questions.json`.
   - [ ] Composite benchmark score $\ge 85\%$.
   - [ ] Unit & benchmark tests pass with 100% success.
   - [ ] Adversarial review completed by `QA-02` with `VERDICT: PASS`.
