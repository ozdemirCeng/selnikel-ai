# Test Results: TASK-003 — Table-Aware Hierarchical Chunking & SHA-256 Deduplication

## 1. Test Suite Execution Output

```text
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\Diley\dev\workspace\selnikel-ai\backend
configfile: pyproject.toml
plugins: anyio-4.14.2, Faker-40.36.0, asyncio-1.4.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 11 items

backend\tests\test_chunker.py ..                                         [ 18%]
backend\tests\test_config.py .                                           [ 27%]
backend\tests\test_health.py ..                                          [ 45%]
backend\tests\test_ingestion_pipeline.py ..                              [ 63%]
backend\tests\test_parser.py ....                                        [100%]

======================= 11 passed in 33.75s =======================
```

## 2. Test Cases Verified
1. `test_table_aware_chunker_preserves_table_and_all_9_metadata_fields`: Verified table preservation, row integrity, and presence of all 9 required metadata fields.
2. `test_chunker_handles_empty_or_small_pages`: Verified zero-chunk graceful return for empty content.
3. `test_sha256_deduplication_detection`: Verified duplicate detection and skip-reparsing logic.
4. `test_ingest_new_document_workflow`: Verified end-to-end flow from byte buffer to database persistence.
