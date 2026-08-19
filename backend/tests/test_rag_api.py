import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, MagicMock
from app.db.session import get_db
from app.domain.document import ChunkMetadata
from app.domain.rag import Citation, GenerationOutput, RetrievalResult
from app.main import app
from app.services.rag.engine import rag_engine


@pytest.mark.asyncio
async def test_rag_query_endpoint(monkeypatch):
    mock_session = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_session

    mock_output = GenerationOutput(
        answer="SB-100 buhar debisi saatte 1000 kg'dır [Belge: SB100.pdf, Sayfa: 2].",
        citations=[
            Citation(
                document_id="doc1",
                filename="SB100.pdf",
                page_number=2,
                snippet="SB-100 debi 1000 kg/h",
                score=0.95,
            )
        ],
        sources_used=["SB100.pdf"],
    )

    monkeypatch.setattr(rag_engine, "query", AsyncMock(return_value=mock_output))

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/rag/query",
            json={"query": "SB-100 debisi nedir?", "top_k": 3},
        )
        assert response.status_code == 200
        data = response.json()
        assert "1000 kg" in data["answer"]
        assert len(data["citations"]) == 1
        assert data["citations"][0]["filename"] == "SB100.pdf"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_rag_stream_endpoint(monkeypatch):
    mock_session = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_session

    async def mock_stream(*args, **kwargs):
        yield "data: {\"type\": \"token\", \"content\": \"Kazan\"}\n\n"
        yield "data: [DONE]\n\n"

    monkeypatch.setattr(rag_engine, "query_stream", mock_stream)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/rag/stream",
            json={"query": "Kazan özellikleri"},
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        body = response.text
        assert "Kazan" in body
        assert "[DONE]" in body

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_rag_history_endpoint(monkeypatch):
    mock_session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_res

    app.dependency_overrides[get_db] = lambda: mock_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/rag/history")
        assert response.status_code == 200
        assert response.json() == []

    app.dependency_overrides.clear()
