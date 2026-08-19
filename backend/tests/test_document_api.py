import io
import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, MagicMock
from app.db.models.document import DocumentModel
from app.db.session import get_db
from app.main import app
from app.services.ingestion.pipeline import ingestion_pipeline


@pytest.fixture
def mock_db_session():
    mock_session = AsyncMock()
    return mock_session


@pytest.mark.asyncio
async def test_upload_empty_file_fails():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        files = {"file": ("empty.txt", io.BytesIO(b""), "text/plain")}
        response = await ac.post("/api/v1/documents/upload", files=files)
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_document_not_found(monkeypatch):
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/documents/non_existent_id_999")
        assert response.status_code == 404

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_document_chunks_not_found():
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/documents/non_existent_id_999/chunks")
        assert response.status_code == 404

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_documents_endpoint(monkeypatch):
    mock_session = AsyncMock()
    
    # Mock count query
    mock_count_res = MagicMock()
    mock_count_res.scalar.return_value = 0
    
    # Mock items query
    mock_items_res = MagicMock()
    mock_items_res.scalars.return_value.all.return_value = []
    
    mock_session.execute.side_effect = [mock_count_res, mock_items_res]
    app.dependency_overrides[get_db] = lambda: mock_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/documents")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    app.dependency_overrides.clear()

