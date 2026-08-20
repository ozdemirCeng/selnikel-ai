"""
Comprehensive Quality Gate & Invariant Tests for Stage P1.2 Golden Benchmark Suite.
Tests:
  1. Schema, dataset integrity, and category distribution (28 items).
  2. Physical fixture grounding, SHA-256 verification, and locator coordinate validity.
  3. Strict OOD and Safety-Critical domain invariants.
  4. Multi-mode CLI execution (self-check, offline-retrieval, full-rag).
  5. Atomic report immutability and metadata tracking.
  6. RBAC security enforcement on /api/v1/evaluation/benchmark (401/403/200).
"""
import json
import os
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.cli.benchmark_runner import run_benchmark
from app.domain.contracts.evaluation import AbstentionReason, BenchmarkQuestion, LocatorType
from app.services.evaluation.dataset_validator import validate_dataset_file
from app.services.evaluation.metrics import extract_parameters

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
        DATASET_PATH, schema_path=SCHEMA_PATH, verify_files_dir=FIXTURES_DIR
    )
    assert is_valid, f"Dataset validation failed: {errors}"
    assert len(errors) == 0

    with open(DATASET_PATH, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    assert len(data) >= 25, f"Expected at least 25 questions, got {len(data)}"
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

        # Verify locator structure
        loc = ev.locator
        assert loc is not None
        if loc.locator_type == LocatorType.TABLE_CELL:
            assert loc.table_id is not None
            assert loc.row_key is not None
            assert loc.column_name is not None
        elif loc.locator_type == LocatorType.SECTION_TEXT:
            assert loc.section_header is not None
            assert loc.key_phrase is not None

    assert in_domain_count == 23


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
    assert report.total_questions == 28
    assert report.passed_questions == 28
    assert report.oracle_mock_used is True
    assert report.network_access == "disabled"
    assert report.safety_compliance_rate == 1.0
    assert report.abstention_rate == 1.0
    assert out_file.exists()


def test_offline_retrieval_mode_execution(tmp_path):
    """Verify offline-retrieval mode indexes synthetic fixtures via BM25 and completes with zero LLM generation."""
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
    assert report.total_questions == 28
    assert report.oracle_mock_used is False
    assert report.network_access == "disabled"
    assert report.mean_recall_at_5 > 0.60
    assert out_file.exists()


def test_full_rag_mode_offline_skipped_invariant(tmp_path, monkeypatch):
    """Verify full-rag mode without LLM credentials cleanly marks report as SKIPPED (never fake PASS)."""
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
    assert report.oracle_mock_used is False
    assert report.network_access == "disabled"
    assert out_file.exists()


@pytest.mark.asyncio
async def test_evaluation_api_rbac_security():
    """Verify /api/v1/evaluation/benchmark enforces RBAC role-gated access (401/403/200)."""
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
        assert data["total_questions"] == 28