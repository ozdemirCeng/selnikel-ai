import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, MagicMock
from app.db.session import get_db
from app.domain.rag import GenerationOutput
from app.main import app
from app.services.rag.engine import rag_engine

AUTH_HEADERS = {"X-Dev-User": "engineer@selnikel.com.tr"}


@pytest.mark.asyncio
async def test_rag_query_unauthenticated_fails():
    """Verify that unauthenticated RAG query returns 401."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post("/api/v1/rag/query", json={"query": "Test query"})
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_rag_query_endpoint(monkeypatch):
    mock_output = GenerationOutput(
        answer="Selnikel SB-Series kazanları 16 bar maksimum basınca sahiptir.",
        citations=[],
        sources_used=["SB-100_Kazan.pdf"],
    )

    monkeypatch.setattr(rag_engine, "query", AsyncMock(return_value=mock_output))

    mock_session = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/rag/query",
            json={"query": "SB serisi kazan basıncı nedir?", "top_k": 3},
            headers=AUTH_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert "16 bar" in data["answer"]
        assert len(data["sources_used"]) == 1

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_rag_stream_endpoint(monkeypatch):
    async def mock_query_stream(*args, **kwargs):
        yield "data: Selnikel Kazan\n\n"
        yield "data: [DONE]\n\n"

    monkeypatch.setattr(rag_engine, "query_stream", mock_query_stream)

    mock_session = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/rag/stream",
            json={"query": "Test stream"},
            headers=AUTH_HEADERS,
        )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_rag_history_endpoint():
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/rag/history", headers=AUTH_HEADERS)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    app.dependency_overrides.clear()
