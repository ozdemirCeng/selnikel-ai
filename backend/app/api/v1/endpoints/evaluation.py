"""
Evaluation API Endpoints.
Provides role-gated access to RAG Golden Benchmark execution and historical reports.
Enforces system.manage RBAC permission.
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.dependencies import require_permission
from app.cli.benchmark_runner import run_benchmark
from app.domain.contracts.evaluation import EvaluationRunReport
from app.domain.identity.models import User

router = APIRouter(prefix="/evaluation", tags=["Evaluation & Benchmarks"])


def get_reports_dir() -> Path:
    """Dependency provider for reports directory. Overridable in tests."""
    backend_dir = Path(__file__).resolve().parent.parent.parent.parent
    d = backend_dir / "app" / "evaluation" / "reports"
    d.mkdir(parents=True, exist_ok=True)
    return d


class BenchmarkRunRequest(BaseModel):
    mode: str = Field(default="offline-retrieval", description="Execution mode: self-check, offline-retrieval, full-rag")
    profile: str = Field(default="memory", description="Retrieval backend profile: memory, qdrant-local")
    category: Optional[str] = Field(default=None, description="Optional category filter")


class BenchmarkRunSummaryResponse(BaseModel):
    run_id: str
    execution_mode: str
    status: str
    total_questions: int
    passed_questions: int
    mean_recall_at_5: float
    mean_ndcg_at_5: float
    mean_numerical_unit_accuracy: float
    mean_citation_precision: float
    mean_faithfulness: float
    safety_compliance_rate: float
    abstention_rate: float
    duration_seconds: float
    report_file: str


@router.post(
    "/benchmark",
    response_model=EvaluationRunReport,
    summary="Trigger RAG Golden Benchmark Evaluation Run",
    status_code=status.HTTP_200_OK,
)
async def trigger_benchmark_run(
    payload: BenchmarkRunRequest,
    user: User = Depends(require_permission("system.manage")),
    reports_dir: Path = Depends(get_reports_dir),
) -> EvaluationRunReport:
    """
    Execute golden benchmark suite.
    Restricted to system administrators with 'system.manage' permission.
    """
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = reports_dir / f"benchmark_report_{payload.mode}_{payload.profile}_{uuid.uuid4().hex[:8]}_{timestamp_str}.json"

    exit_code, report, report_path = run_benchmark(
        mode=payload.mode,
        profile=payload.profile,
        category_filter=payload.category,
        output_path=out_path,
    )

    if not report:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Benchmark execution failed to produce a valid report.",
        )

    return report


@router.get(
    "/reports",
    response_model=List[BenchmarkRunSummaryResponse],
    summary="List historical benchmark reports",
    status_code=status.HTTP_200_OK,
)
async def list_benchmark_reports(
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(require_permission("system.manage")),
    reports_dir: Path = Depends(get_reports_dir),
) -> List[BenchmarkRunSummaryResponse]:
    """
    Retrieve history of executed benchmark reports.
    Requires 'system.manage' permission.
    """
    if not reports_dir.exists():
        return []

    summaries = []
    for report_file in sorted(reports_dir.glob("benchmark_report_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
        try:
            with open(report_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            summaries.append(
                BenchmarkRunSummaryResponse(
                    run_id=data.get("run_id", ""),
                    execution_mode=data.get("execution_mode", "unknown"),
                    status=data.get("status", "COMPLETED"),
                    total_questions=data.get("total_questions", 0),
                    passed_questions=data.get("passed_questions", 0),
                    mean_recall_at_5=data.get("mean_recall_at_5", 0.0),
                    mean_ndcg_at_5=data.get("mean_ndcg_at_5", 0.0),
                    mean_numerical_unit_accuracy=data.get("mean_numerical_unit_accuracy", 0.0),
                    mean_citation_precision=data.get("mean_citation_precision", 0.0),
                    mean_faithfulness=data.get("mean_faithfulness", 0.0),
                    safety_compliance_rate=data.get("safety_compliance_rate", 0.0),
                    abstention_rate=data.get("abstention_rate", 0.0),
                    duration_seconds=data.get("duration_seconds", 0.0),
                    report_file=report_file.name,
                )
            )
        except Exception:
            continue

    return summaries