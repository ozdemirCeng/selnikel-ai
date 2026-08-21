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
async def test_burner_combustion_calculation():
    from app.services.agent.tools.burner_calc import BurnerCombustionTool

    args = {
        "fuel_consumption_rate": 250.0,
        "fuel_type": "natural_gas",
        "flue_gas_temp_c": 160.0,
        "ambient_temp_c": 20.0,
        "o2_dry_percent": 3.0,
    }
    result = await BurnerCombustionTool.execute(args)

    assert result["fuel_consumption_rate"] == 250.0
    assert result["excess_air_ratio_lambda"] > 1.10
    assert result["combustion_air_flow_nm3_h"] > 2500.0
    assert result["flue_gas_loss_percent"] > 0
    assert result["combustion_efficiency_percent"] > 90.0
    assert "Siegert" in result["standard_applied"]


@pytest.mark.asyncio
async def test_economizer_heat_recovery_calculation():
    from app.services.agent.tools.economizer_calc import EconomizerHeatRecoveryTool

    args = {
        "steam_flow_kg_h": 5000.0,
        "flue_gas_inlet_temp_c": 220.0,
        "flue_gas_outlet_temp_c": 130.0,
        "feedwater_inlet_temp_c": 85.0,
        "operating_hours_per_year": 6000.0,
        "fuel_type": "natural_gas",
    }
    result = await EconomizerHeatRecoveryTool.execute(args)

    assert result["steam_flow_kg_h"] == 5000.0
    assert result["flue_gas_temp_drop_c"] == 90.0
    assert result["recovered_power_kw"] > 150.0
    assert result["feedwater_temp_rise_c"] > 20.0
    assert result["efficiency_gain_percent"] == 4.5
    assert result["annual_fuel_savings"] > 50000.0


@pytest.mark.asyncio
async def test_safety_valve_sizing_calculation():
    from app.services.agent.tools.safety_valve_calc import SafetyValveSizingTool

    args = {
        "boiler_capacity_kg_h": 5000.0,
        "set_pressure_bar_g": 16.0,
        "overpressure_percent": 10.0,
        "derated_discharge_coefficient": 0.70,
    }
    result = await SafetyValveSizingTool.execute(args)

    assert result["boiler_capacity_kg_h"] == 5000.0
    assert result["relieving_pressure_bar_abs"] > 18.0
    assert result["calculated_orifice_area_mm2"] > 500.0
    assert result["calculated_orifice_diameter_mm"] > 25.0
    assert result["recommended_dn_inlet"] in (25, 32, 40, 50, 65, 80, 100)
    assert "EN ISO 4126-1" in result["standards_compliance"]


@pytest.mark.asyncio
async def test_agent_orchestrator_multi_step_flow():
    mock_llm = AsyncMock()

    # Step 1: Agent calls calculate_boiler_efficiency
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
