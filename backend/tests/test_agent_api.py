import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, patch
from app.main import app


@pytest.mark.asyncio
async def test_get_agent_tools():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/agent/tools")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 4
    tool_names = [t["name"] for t in data]
    assert "search_engineering_documents" in tool_names
    assert "calculate_boiler_efficiency" in tool_names
    assert "calculate_fan_airflow" in tool_names
    assert "generate_engineering_report" in tool_names


@pytest.mark.asyncio
async def test_run_agent_endpoint_validation():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Empty query validation
        response = await ac.post("/api/v1/agent/run", json={"query": ""})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_run_agent_endpoint_success():
    with patch(
        "app.services.agent.orchestrator.engineering_agent.run",
        new_callable=AsyncMock,
    ) as mock_run:
        mock_run.return_value = {
            "query": "Kazan verimi nedir?",
            "final_answer": "Termal verim %91.5 olarak hesaplanmıştır.",
            "steps": [],
            "tools_used": ["calculate_boiler_efficiency"],
            "total_execution_time_ms": 120.5,
        }

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/api/v1/agent/run",
                json={"query": "Kazan verimi nedir?"},
            )
        assert response.status_code == 200
        data = response.json()
        assert "Termal verim %91.5" in data["final_answer"]
        assert "calculate_boiler_efficiency" in data["tools_used"]


@pytest.mark.asyncio
async def test_stream_agent_endpoint_success():
    with patch(
        "app.services.agent.orchestrator.engineering_agent.run",
        new_callable=AsyncMock,
    ) as mock_run:
        from app.domain.agent import AgentExecutionResponse
        mock_run.return_value = AgentExecutionResponse(
            query="Fan debisi nedir?",
            final_answer="Fan debisi 15000 m3/h'dir.",
            steps=[],
            tools_used=["calculate_fan_airflow"],
            total_execution_time_ms=95.0,
        )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/api/v1/agent/stream",
                json={"query": "Fan debisi nedir?"},
            )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        assert "Fan debisi 15000" in response.text
