import pytest
from unittest.mock import AsyncMock
from app.services.agent.orchestrator import EngineeringAgentOrchestrator
from app.services.agent.tools.boiler_calc import BoilerEfficiencyTool
from app.services.agent.tools.fan_calc import FanAirflowTool
from app.services.agent.tools.report_gen import ReportGeneratorTool
from app.services.agent.tools.search_docs import SearchDocumentsTool


@pytest.mark.asyncio
async def test_boiler_efficiency_calculation():
    args = {
        "steam_flow_kg_h": 2000.0,
        "steam_pressure_bar": 16.0,
        "feedwater_temp_c": 105.0,
        "fuel_type": "natural_gas",
        "boiler_efficiency_percent": 92.0,
    }
    result = await BoilerEfficiencyTool.execute(args)

    assert result["steam_flow_kg_h"] == 2000.0
    assert result["thermal_output_kw"] > 1000.0
    assert result["fuel_consumption_rate"] > 0
    assert result["fuel_unit"] == "Nm3/h"


@pytest.mark.asyncio
async def test_fan_airflow_calculation():
    args = {
        "duct_diameter_mm": 600.0,
        "air_velocity_m_s": 20.0,
        "total_pressure_pa": 1500.0,
        "fan_efficiency_percent": 80.0,
    }
    result = await FanAirflowTool.execute(args)

    assert result["duct_diameter_mm"] == 600.0
    assert result["flow_rate_m3_h"] > 15000.0
    assert result["shaft_power_kw"] > 0
    assert result["recommended_motor_power_kw"] > result["shaft_power_kw"]


@pytest.mark.asyncio
async def test_report_generator_tool():
    args = {
        "title": "Kazan Test Raporu",
        "equipment_model": "SB-100",
        "executive_summary": "Test başarıyla tamamlandı.",
        "calculation_results": {"thermal_efficiency": "91.8%", "steam_capacity": "1000 kg/h"},
        "citations": [{"filename": "SB100.pdf", "page_number": 4}],
    }
    result = await ReportGeneratorTool.execute(args)

    assert result["report_title"] == "Kazan Test Raporu"
    assert "SELNİKEL ENERJİ" in result["markdown_content"]
    assert "SB-100" in result["markdown_content"]
    assert "91.8%" in result["markdown_content"]


@pytest.mark.asyncio
async def test_agent_orchestrator_multi_step_flow():
    mock_llm = AsyncMock()

    # Step 1: Agent calls search_engineering_documents
    step1_response = '```json\n{\n  "thought": "Önce kazan verisini aramalıyım.",\n  "action": "calculate_boiler_efficiency",\n  "action_input": {"steam_flow_kg_h": 1000, "steam_pressure_bar": 16}\n}\n```'
    # Step 2: Agent synthesizes final answer
    step2_response = '```json\n{\n  "thought": "Hesaplama tamamlandı.",\n  "final_answer": "SB-100 buhar debisi 1000 kg/h için gerekli doğal gaz tüketimi saatte ~70 Nm3/h olarak hesaplanmıştır."\n}\n```'

    mock_llm.generate.side_effect = [step1_response, step2_response]

    agent = EngineeringAgentOrchestrator(llm=mock_llm)
    response = await agent.run("SB-100 yakıt tüketimi ne kadardır?", max_steps=3)

    assert len(response.steps) == 2
    assert "calculate_boiler_efficiency" in response.tools_used
    assert "70 Nm3/h" in response.final_answer
    assert response.steps[0].tool_result is not None
    assert response.steps[0].tool_result.success is True
