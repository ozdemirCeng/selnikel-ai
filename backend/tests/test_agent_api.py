import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock
from app.main import app
from app.domain.agent import AgentExecutionResponse
from app.services.agent.orchestrator import engineering_agent

AUTH_HEADERS = {"X-Dev-User": "engineer@selnikel.com.tr"}


@pytest.mark.asyncio
async def test_get_agent_tools():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/agent/tools", headers=AUTH_HEADERS)
        assert response.status_code == 200
        tools = response.json()
        assert len(tools) >= 3
        tool_names = [t["name"] for t in tools]
        assert "calculate_boiler_efficiency" in tool_names
        assert "calculate_fan_airflow" in tool_names


@pytest.mark.asyncio
async def test_run_agent_endpoint_validation():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post("/api/v1/agent/run", json={"query": ""}, headers=AUTH_HEADERS)
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_run_agent_endpoint_success(monkeypatch):
    mock_resp = AgentExecutionResponse(
        final_answer="SB-100 kazan verimi %91.5 olarak hesaplanmıştır.",
        query="Kazan verimini hesapla",
        steps=[],
        tools_used=["calculate_boiler_efficiency"],
        total_execution_time_ms=120.0,
    )
    monkeypatch.setattr(engineering_agent, "run", AsyncMock(return_value=mock_resp))

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/agent/run",
            json={"query": "Kazan verimini hesapla", "max_steps": 3},
            headers=AUTH_HEADERS,
        )
        assert response.status_code == 200
        data = response.json()
        assert "91.5" in data["final_answer"]
        assert "calculate_boiler_efficiency" in data["tools_used"]


@pytest.mark.asyncio
async def test_stream_agent_endpoint_success(monkeypatch):
    async def mock_stream_run(*args, **kwargs):
        yield {"type": "thought", "content": "Hesaplama başlatılıyor..."}
        yield {"type": "answer_token", "content": "Sonuç: %91.5"}

    monkeypatch.setattr(engineering_agent, "stream_run", mock_stream_run)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/agent/stream",
            json={"query": "Kazan verimi", "max_steps": 2},
            headers=AUTH_HEADERS,
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
