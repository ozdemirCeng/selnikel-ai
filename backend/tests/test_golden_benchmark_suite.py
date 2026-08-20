"""
Comprehensive Quality Gate & Invariant Tests for Stage P1.2 Golden Benchmark Suite.
Tests:
  1. Schema, dataset integrity, and category distribution (28 items).
  2. Physical fixture grounding, SHA-256 verification, and locator coordinate validity with mandatory expected_cell_value.
  3. Strict OOD and Safety-Critical domain invariants.
  4. Fail-fast coordinate validator against corrupted revision/page/table/column/row/section/phrase/cell_value locators.
  5. Multi-mode CLI execution (self-check, offline-retrieval, full-rag).
  6. Profile-based retriever dispatch (memory vs qdrant-local health check).
  7. Full-RAG end-to-end engine contract with indexed real fixture chunks, non-empty retrieval & verified citation assertions.
  8. Runner-level atomic report immutability guarantee (FileExistsError).
  9. RBAC security enforcement on /api/v1/evaluation/benchmark with isolated temp report dir.
"""
import copy
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.api.v1.endpoints.evaluation import get_reports_dir
from app.cli.benchmark_runner import run_benchmark, write_atomic_json
from app.domain.contracts.evaluation import AbstentionReason, BenchmarkQuestion, LocatorType
from app.domain.rag import Citation, GenerationOutput, RetrievalResult
from app.services.evaluation.dataset_validator import validate_dataset_file
from app.services.evaluation.evaluator import RAGBenchmarkEvaluator
from app.services.evaluation.metrics import extract_parameters
from app.services.ingestion.chunker import TableAwareChunker
from app.services.ingestion.parser import FastFallbackParser
from app.services.llm.base import BaseLLMProvider
from app.services.rag.engine import DeterministicRAGEngine
from app.services.retrieval.in_memory_bm25 import InMemoryBM25Index

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATASET_PATH = BACKEND_DIR / "app" / "evaluation" / "datasets" / "golden_benchmark_v1.json"
SCHEMA_PATH = BACKEND_DIR / "app" / "evaluation" / "schemas" / "golden_benchmark_v1.schema.json"
MANIFEST_PATH = BACKEND_DIR / "tests" / "fixtures" / "fixture_manifest.json"
FIXTURES_DIR = BACKEND_DIR / "tests" / "fixtures" / "documents"


def test_golden_benchmark_schema_and_dataset_integrity():
    """Verify golden_benchmark_v1.json conforms to JSON Schema and domain validator."""
    assert DATASET_PATH.exists(), f"Missing dataset: {DATASET_PATH}"
    assert SCHEMA_PATH.exists(), f"Missing schema: {SCHEMA_PATH}"

    is_valid, errors = validate_dataset_file(
        DATASET_PATH, schema_path=SCHEMA_PATH, verify_files_dir=FIXTURES_DIR, manifest_path=MANIFEST_PATH
    )
    assert is_valid, f"Dataset validation failed: {errors}"
    assert len(errors) == 0

    with open(DATASET_PATH, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    assert len(data) == 28

    categories = {item["category"] for item in data}
    expected_categories = {
        "capacity_pressure_temp",
        "maintenance_intervals",
        "fault_troubleshooting",
        "parts_compatibility",
        "standards_compliance",
        "revision_conflicts",
        "out_of_domain",
        "safety_critical",
    }
    assert expected_categories.issubset(categories)


def test_parametric_grounding_against_physical_manifest():
    """Verify every in-domain question is grounded in physical files with matching SHA-256 and coordinates."""
    with open(DATASET_PATH, "r", encoding="utf-8-sig") as df:
        questions_raw = json.load(df)

    with open(MANIFEST_PATH, "r", encoding="utf-8-sig") as mf:
        manifest = json.load(mf)

    manifest_fixtures = {fix["filename"]: fix for fix in manifest["fixtures"]}

    in_domain_count = 0
    for item in questions_raw:
        q = BenchmarkQuestion(**item)
        if q.is_out_of_domain:
            continue

        in_domain_count += 1
        ev = q.expected_evidence
        assert ev is not None
        assert ev.document_name in manifest_fixtures, f"Unknown document '{ev.document_name}' in question '{q.id}'"

        fix_meta = manifest_fixtures[ev.document_name]
        assert ev.document_sha256 == fix_meta["sha256"]
        assert ev.revision_code == fix_meta["revision_code"]
        assert 1 <= ev.page_number <= fix_meta["page_count"]

        # Verify parameter parseability
        for p in ev.expected_numerical_parameters:
            parsed = extract_parameters(p)
            assert len(parsed) > 0, f"Failed to extract parameter from '{p}' in question '{q.id}'"

        # Verify locator structure & mandatory expected_cell_value
        loc = ev.locator
        assert loc is not None
        if loc.locator_type == LocatorType.TABLE_CELL:
            assert loc.table_id is not None
            assert loc.row_key is not None
            assert loc.column_name is not None
            assert loc.expected_cell_value is not None, f"Question '{q.id}' missing expected_cell_value"
        elif loc.locator_type == LocatorType.SECTION_TEXT:
            assert loc.section_header is not None
            assert loc.key_phrase is not None

    assert in_domain_count == 23


def test_fail_fast_coordinate_mutations(tmp_path):
    """Verify validator strictly catches fake_table, fake_column, fake_section, fake_row, wrong_column, wrong_row, wrong_cell_value."""
    with open(DATASET_PATH, "r", encoding="utf-8-sig") as f:
        base_data = json.load(f)

    # 1. Mutate table_id (fake_table)
    mut_tab = copy.deepcopy(base_data)
    mut_tab[0]["expected_evidence"]["locator"]["table_id"] = "fake_table_999"
    p_tab = tmp_path / "mut_tab.json"
    with open(p_tab, "w", encoding="utf-8") as f:
        json.dump(mut_tab, f)
    v_tab, err_tab = validate_dataset_file(p_tab, SCHEMA_PATH, FIXTURES_DIR, MANIFEST_PATH)
    assert not v_tab
    assert any("table_id 'fake_table_999' not found" in e for e in err_tab)

    # 2. Mutate column_name to nonexistent column (fake_column)
    mut_col = copy.deepcopy(base_data)
    mut_col[0]["expected_evidence"]["locator"]["column_name"] = "fake_column_xyz"
    p_col = tmp_path / "mut_col.json"
    with open(p_col, "w", encoding="utf-8") as f:
        json.dump(mut_col, f)
    v_col, err_col = validate_dataset_file(p_col, SCHEMA_PATH, FIXTURES_DIR, MANIFEST_PATH)
    assert not v_col
    assert any("column_name 'fake_column_xyz' not found" in e for e in err_col)

    # 3. Mutate column_name to valid column in table, but WRONG column for ground truth (wrong_column)
    # Question 0: SB-500 design_press expected_cell_value is "16.0 bar". Mutating column to "steam_cap" (which is "0.5")
    mut_wcol = copy.deepcopy(base_data)
    mut_wcol[0]["expected_evidence"]["locator"]["column_name"] = "steam_cap"
    p_wcol = tmp_path / "mut_wcol.json"
    with open(p_wcol, "w", encoding="utf-8") as f:
        json.dump(mut_wcol, f)
    v_wcol, err_wcol = validate_dataset_file(p_wcol, SCHEMA_PATH, FIXTURES_DIR, MANIFEST_PATH)
    assert not v_wcol
    assert any("expected cell value '16.0 bar', but found '0.5 t/h'" in e for e in err_wcol)

    # 4. Mutate row_key to nonexistent row (fake_row)
    mut_row = copy.deepcopy(base_data)
    mut_row[0]["expected_evidence"]["locator"]["row_key"] = "NONEXISTENT_ROW_KEY_XYZ"
    p_row = tmp_path / "mut_row.json"
    with open(p_row, "w", encoding="utf-8") as f:
        json.dump(mut_row, f)
    v_row, err_row = validate_dataset_file(p_row, SCHEMA_PATH, FIXTURES_DIR, MANIFEST_PATH)
    assert not v_row
    assert any("row_key 'NONEXISTENT_ROW_KEY_XYZ' not found" in e for e in err_row)

    # 5. Mutate row_key to valid row in table, but WRONG row for ground truth (wrong_row)
    # Question 16: SB-1000 steam_cap is "0.9 t/h". Mutating row to "SB-500" (which has steam_cap "0.5")
    mut_wrow = copy.deepcopy(base_data)
    mut_wrow[16]["expected_evidence"]["locator"]["row_key"] = "SB-500"
    p_wrow = tmp_path / "mut_wrow.json"
    with open(p_wrow, "w", encoding="utf-8") as f:
        json.dump(mut_wrow, f)
    v_wrow, err_wrow = validate_dataset_file(p_wrow, SCHEMA_PATH, FIXTURES_DIR, MANIFEST_PATH)
    assert not v_wrow
    assert any("expected cell value" in e for e in err_wrow)

    # 6. Mutate expected_cell_value directly (wrong_cell_value)
    mut_val = copy.deepcopy(base_data)
    mut_val[0]["expected_evidence"]["locator"]["expected_cell_value"] = "999.0 bar"
    p_val = tmp_path / "mut_val.json"
    with open(p_val, "w", encoding="utf-8") as f:
        json.dump(mut_val, f)
    v_val, err_val = validate_dataset_file(p_val, SCHEMA_PATH, FIXTURES_DIR, MANIFEST_PATH)
    assert not v_val
    assert any("expected cell value '999.0 bar', but found '16.0 bar'" in e for e in err_val)

    # 7. Mutate table_cell locator by removing expected_cell_value (missing_expected_cell_value)
    mut_nval = copy.deepcopy(base_data)
    mut_nval[0]["expected_evidence"]["locator"]["expected_cell_value"] = None
    p_nval = tmp_path / "mut_nval.json"
    with open(p_nval, "w", encoding="utf-8") as f:
        json.dump(mut_nval, f)
    v_nval, err_nval = validate_dataset_file(p_nval, SCHEMA_PATH, FIXTURES_DIR, MANIFEST_PATH)
    assert not v_nval
    assert any("missing required 'expected_cell_value'" in e for e in err_nval)

    # 8. Mutate section_header (fake_section)
    mut_sec = copy.deepcopy(base_data)
    mut_sec[9]["expected_evidence"]["locator"]["section_header"] = "Nonexistent Safety Section 999"
    p_sec = tmp_path / "mut_sec.json"
    with open(p_sec, "w", encoding="utf-8") as f:
        json.dump(mut_sec, f)
    v_sec, err_sec = validate_dataset_file(p_sec, SCHEMA_PATH, FIXTURES_DIR, MANIFEST_PATH)
    assert not v_sec
    assert any("section_header 'Nonexistent Safety Section 999' not found" in e for e in err_sec)

    # 9. Mutate key_phrase (fake_phrase)
    mut_phr = copy.deepcopy(base_data)
    mut_phr[9]["expected_evidence"]["locator"]["key_phrase"] = "Nonexistent Key Phrase XYZ 123"
    p_phr = tmp_path / "mut_phr.json"
    with open(p_phr, "w", encoding="utf-8") as f:
        json.dump(mut_phr, f)
    v_phr, err_phr = validate_dataset_file(p_phr, SCHEMA_PATH, FIXTURES_DIR, MANIFEST_PATH)
    assert not v_phr
    assert any("key_phrase 'Nonexistent Key Phrase XYZ 123' not found" in e for e in err_phr)

    # 10. Mutate revision_code
    mut_rev = copy.deepcopy(base_data)
    mut_rev[0]["expected_evidence"]["revision_code"] = "FAKE-REV"
    p_rev = tmp_path / "mut_rev.json"
    with open(p_rev, "w", encoding="utf-8") as f:
        json.dump(mut_rev, f)
    v_rev, err_rev = validate_dataset_file(p_rev, SCHEMA_PATH, FIXTURES_DIR, MANIFEST_PATH)
    assert not v_rev
    assert any("revision_code mismatch" in e for e in err_rev)

    # 11. Mutate page_number
    mut_pg = copy.deepcopy(base_data)
    mut_pg[0]["expected_evidence"]["page_number"] = 999
    p_pg = tmp_path / "mut_pg.json"
    with open(p_pg, "w", encoding="utf-8") as f:
        json.dump(mut_pg, f)
    v_pg, err_pg = validate_dataset_file(p_pg, SCHEMA_PATH, FIXTURES_DIR, MANIFEST_PATH)
    assert not v_pg
    assert any("exceeds manifest page_count" in e or "exceeds parsed document" in e for e in err_pg)


def test_out_of_domain_and_safety_critical_invariants():
    """Verify strict conditional branch enforcement for OOD and safety-critical items."""
    with open(DATASET_PATH, "r", encoding="utf-8-sig") as df:
        questions_raw = json.load(df)

    ood_items = [q for q in questions_raw if q.get("is_out_of_domain")]
    assert len(ood_items) == 5

    for ood in ood_items:
        assert ood["expected_evidence"] is None
        assert ood["abstention_expected"] is True
        assert ood["expected_abstention_reason"] == "out_of_domain"

    safety_items = [q for q in questions_raw if q.get("is_safety_critical")]
    assert len(safety_items) == 5

    for sc in safety_items:
        assert sc["expected_evidence"] is not None
        assert len(sc["expected_evidence"]["expected_numerical_parameters"]) > 0


def test_evaluator_self_check_mode_execution(tmp_path):
    """Verify self-check mode runs cleanly, verifies 100% control pairs, and records oracle_mock_used."""
    out_file = tmp_path / "self_check_test_report.json"
    exit_code, report, report_path = run_benchmark(
        mode="self-check",
        output_path=out_file,
    )

    assert exit_code == 0
    assert report is not None
    assert report.execution_mode == "self-check"
    assert report.status == "COMPLETED"
    assert report.gate_status == "PASSED"
    assert report.total_questions == 28
    assert report.passed_questions == 28
    assert report.oracle_mock_used is True
    assert report.network_access == "disabled"
    assert report.safety_compliance_rate == 1.0
    assert report.abstention_rate == 1.0
    assert out_file.exists()


def test_offline_retrieval_mode_execution(tmp_path):
    """Verify offline-retrieval mode evaluates pure retrieval metrics without fake generation."""
    out_file = tmp_path / "offline_retrieval_test_report.json"
    exit_code, report, report_path = run_benchmark(
        mode="offline-retrieval",
        profile="memory",
        output_path=out_file,
    )

    assert exit_code == 0
    assert report is not None
    assert report.execution_mode == "offline-retrieval"
    assert report.status == "COMPLETED"
    assert report.gate_status == "PASSED"
    assert report.total_questions == 28
    assert report.passed_questions == 19  # Exactly 19 / 23 in-domain items passed (OOD not inflated)
    assert report.oracle_mock_used is False
    assert report.network_access == "disabled"
    assert report.model_name == "retrieval-memory-bm25"
    assert report.mean_recall_at_5 >= 0.75  # In-domain recall is 0.8261
    assert report.mean_citation_precision == 0.0  # Pure retrieval - zero fake generation
    assert report.mean_faithfulness == 0.0
    assert report.abstention_rate == 1.0
    assert out_file.exists()


def test_qdrant_local_profile_handling(tmp_path):
    """Verify qdrant-local profile checks health and fails fast if offline."""
    out_file = tmp_path / "qdrant_local_test_report.json"
    exit_code, report, report_path = run_benchmark(
        mode="offline-retrieval",
        profile="qdrant-local",
        output_path=out_file,
    )

    if exit_code == 1:
        assert report.status == "FAILED"
        assert report.gate_status == "FAILED"
        assert any("Qdrant" in r for r in report.gate_failure_reasons)
    else:
        assert report.status == "COMPLETED"
        assert report.network_access == "local_only"


class MockLLMProvider(BaseLLMProvider):
    """Deterministic Mock LLM Provider for Full-RAG pipeline testing."""
    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        return "The SB-500 steam boiler has steam capacity of 0.5 t/h and design pressure of 16.0 bar. [Doc: SB_Series_Steam_Boiler_Datasheet.pdf, P. 2]"

    async def stream(self, prompt: str, system_prompt: Optional[str] = None, **kwargs):
        yield "The SB-500 steam boiler has steam capacity of 0.5 t/h and design pressure of 16.0 bar. [Doc: SB_Series_Steam_Boiler_Datasheet.pdf, P. 2]"

    async def check_health(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_full_rag_pipeline_end_to_end():
    """
    Verify DeterministicRAGEngine query_with_retrieval contract runs end-to-end with:
      - Real ingested fixture chunks from disk
      - Non-empty hybrid retrieval
      - Live citation extraction & verification
      - Full evaluator scoring
    """
    # 1. Parse and chunk real fixtures
    parser = FastFallbackParser()
    chunker = TableAwareChunker(max_chunk_chars=800, chunk_overlap_chars=100)
    all_chunks = []
    for fix_file in sorted(FIXTURES_DIR.glob("*")):
        if fix_file.is_file() and fix_file.suffix.lower() in [".pdf", ".docx", ".txt"]:
            pdoc = parser.parse_sync(str(fix_file))
            chunks = chunker.chunk_document(pdoc, document_id=fix_file.name)
            all_chunks.extend(chunks)

    assert len(all_chunks) > 0, "Fixtures must produce parsed chunks"

    # 2. Index into BM25
    bm25 = InMemoryBM25Index()
    bm25.index_chunks(all_chunks)

    # 3. Instantiate Engine with Mock Provider
    llm = MockLLMProvider()
    rag_engine = DeterministicRAGEngine(retriever=bm25, llm=llm)

    # 4. Execute query_with_retrieval for question 0
    evaluator = RAGBenchmarkEvaluator(dataset_path=DATASET_PATH)
    q0 = evaluator.questions[0]
    output, retrieved = await rag_engine.query_with_retrieval(q0.question, top_k=5)

    # 5. Assertions on retrieved chunks and generation output
    assert isinstance(output, GenerationOutput)
    assert "16.0 bar" in output.answer
    assert "0.5 t/h" in output.answer
    assert isinstance(retrieved, list)
    assert len(retrieved) > 0, "Retriever must return non-empty candidate chunks"
    assert any("SB-500" in c.content for c in retrieved), "Retrieved chunks must contain SB-500 target chunk"

    # 6. Assertions on citations
    assert len(output.citations) > 0, "Citation engine must extract citations from grounded answer"
    assert output.citations[0].filename in ["SB_Series_Steam_Boiler_Datasheet.pdf", "SB_Series_Steam_Boiler_Datasheet_REV01.pdf"]
    assert output.citations[0].page_number == 2

    # 7. Full evaluator scoring
    item_res = evaluator.evaluate_single(q0, output, retrieved)
    assert item_res.question_id == q0.id
    assert item_res.metrics.numerical_unit_accuracy == 1.0
    assert item_res.metrics.citation_precision == 1.0
    assert item_res.metrics.recall_at_5 == 1.0
    assert item_res.passed is True


def test_full_rag_mode_offline_skipped_invariant(tmp_path, monkeypatch):
    """Verify full-rag mode without live LLM generator cleanly marks report as SKIPPED with exit code 0."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("LOCAL_LLM_URL", raising=False)

    out_file = tmp_path / "full_rag_skipped_report.json"
    exit_code, report, report_path = run_benchmark(
        mode="full-rag",
        output_path=out_file,
    )

    assert exit_code == 0
    assert report is not None
    assert report.execution_mode == "full-rag"
    assert report.status == "SKIPPED"
    assert report.gate_status == "SKIPPED"
    assert report.oracle_mock_used is False
    assert report.network_access == "disabled"
    assert out_file.exists()


def test_runner_report_immutability_guarantee(tmp_path):
    """Verify run_benchmark enforces immutability at runner level and requires overwrite=True."""
    target = tmp_path / "runner_immutable_report.json"
    exit_code, report, _ = run_benchmark(mode="self-check", output_path=target, overwrite_report=False)
    assert target.exists()
    assert exit_code == 0

    # Running again without overwrite_report must raise FileExistsError
    with pytest.raises(FileExistsError):
        run_benchmark(mode="self-check", output_path=target, overwrite_report=False)

    # Running with overwrite_report=True succeeds
    exit_code2, report2, _ = run_benchmark(mode="self-check", output_path=target, overwrite_report=True)
    assert exit_code2 == 0


@pytest.mark.asyncio
async def test_evaluation_api_rbac_security(tmp_path):
    """Verify /api/v1/evaluation/benchmark enforces RBAC role-gated access (401/403/200) and uses isolated reports dir."""
    app.dependency_overrides[get_reports_dir] = lambda: tmp_path
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Unauthenticated -> 401 Unauthorized
            res_unauth = await client.post(
                "/api/v1/evaluation/benchmark",
                json={"mode": "self-check", "profile": "memory"},
            )
            assert res_unauth.status_code == 401, f"Expected 401, got {res_unauth.status_code}: {res_unauth.text}"

            # 2. Regular Engineer without system.manage -> 403 Forbidden
            res_forbidden = await client.post(
                "/api/v1/evaluation/benchmark",
                json={"mode": "self-check", "profile": "memory"},
                headers={"Authorization": "Bearer dev-token-engineer@selnikel.com.tr"},
            )
            assert res_forbidden.status_code == 403, f"Expected 403, got {res_forbidden.status_code}: {res_forbidden.text}"

            # 3. Super Admin with system.manage -> 200 OK
            res_ok = await client.post(
                "/api/v1/evaluation/benchmark",
                json={"mode": "self-check", "profile": "memory"},
                headers={"Authorization": "Bearer dev-token-admin@selnikel.com.tr"},
            )
            assert res_ok.status_code == 200, f"Expected 200, got {res_ok.status_code}: {res_ok.text}"
            data = res_ok.json()
            assert data["execution_mode"] == "self-check"
            assert data["status"] == "COMPLETED"
            assert data["gate_status"] == "PASSED"
            assert data["total_questions"] == 28

            # Verify report was written into tmp_path, NOT into workspace!
            created_reports = list(tmp_path.glob("benchmark_report_*.json"))
            assert len(created_reports) >= 1
    finally:
        app.dependency_overrides.pop(get_reports_dir, None)