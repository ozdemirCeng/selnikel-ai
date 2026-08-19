# Test Results: TASK-008 — Grounded Industrial Prompt Design & Citation Formatting Engine

## 1. Test Suite Execution Output

```text
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\Diley\dev\workspace\selnikel-ai\backend
configfile: pyproject.toml
plugins: anyio-4.14.2, Faker-40.36.0, asyncio-1.4.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 4 items

backend\tests\test_grounding.py ....                                     [100%]

============================== 4 passed in 1.73s ==============================
```

## 2. Test Cases Verified
1. `test_system_prompt_rules_contain_grounding_and_refusal`: Validates presence of strict context rules, refusal phrases, and citation guidelines.
2. `test_build_rag_user_prompt_formats_context`: Validates context header assembly, page numbers, and query placement.
3. `test_citation_engine_extracts_inline_citations`: Validates regex extraction, page mapping, document ID lookup, and source deduplication.
4. `test_citation_engine_handles_refusal`: Validates zero-citation generation on refusal.
