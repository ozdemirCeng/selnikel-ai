import time
from fastapi import APIRouter
from app.core.config import settings
from app.infrastructure.db import check_db_connection
from app.infrastructure.qdrant import qdrant_repo
from app.schemas.health import HealthCheckResponse, ServiceComponentStatus
from app.services.llm import llm_provider

router = APIRouter()


@router.get("", response_model=HealthCheckResponse, summary="Comprehensive System Health Check")
async def health_check() -> HealthCheckResponse:
    components = {}
    overall_healthy = True

    # 1. Database Check
    db_start = time.perf_counter()
    db_ok = await check_db_connection()
    db_latency = (time.perf_counter() - db_start) * 1000
    components["database"] = ServiceComponentStatus(
        status="healthy" if db_ok else "unhealthy",
        latency_ms=round(db_latency, 2),
        details="PostgreSQL connection verified" if db_ok else "Unable to connect to PostgreSQL",
    )
    if not db_ok:
        overall_healthy = False

    # 2. Qdrant Vector DB Check
    qdrant_start = time.perf_counter()
    qdrant_ok = await qdrant_repo.check_health()
    qdrant_latency = (time.perf_counter() - qdrant_start) * 1000
    components["vector_db"] = ServiceComponentStatus(
        status="healthy" if qdrant_ok else "unhealthy",
        latency_ms=round(qdrant_latency, 2),
        details="Qdrant vector engine reachable" if qdrant_ok else "Unable to reach Qdrant",
    )
    if not qdrant_ok:
        overall_healthy = False

    # 3. LLM Provider Status
    llm_start = time.perf_counter()
    llm_ok = await llm_provider.check_health()
    llm_latency = (time.perf_counter() - llm_start) * 1000
    components["llm_provider"] = ServiceComponentStatus(
        status="healthy" if llm_ok else "disabled",
        latency_ms=round(llm_latency, 2),
        details=f"Provider '{settings.LLM_PROVIDER}' (Model: {settings.LLM_MODEL if settings.LLM_PROVIDER == 'openai' else settings.OLLAMA_MODEL})",
    )

    return HealthCheckResponse(
        status="healthy" if overall_healthy else "degraded",
        project=settings.PROJECT_NAME,
        environment=settings.ENVIRONMENT,
        version="0.1.0",
        components=components,
    )
