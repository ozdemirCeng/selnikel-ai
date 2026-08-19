from typing import Any, Dict
from app.domain.agent import ToolDefinition, ToolParameter


class BoilerEfficiencyTool:
    """Tool to calculate industrial steam boiler thermal efficiency and fuel consumption (ASME PTC 4.1)."""

    @classmethod
    def get_definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="calculate_boiler_efficiency",
            description="Calculates industrial boiler thermal efficiency (%), useful thermal output (kW/MW), and required fuel consumption based on steam flow rate, pressure, feedwater temperature, and fuel lower heating value (LHV).",
            parameters=[
                ToolParameter(
                    name="steam_flow_kg_h",
                    type="number",
                    description="Steam generation rate in kg/h (e.g. 1000).",
                    required=True,
                ),
                ToolParameter(
                    name="steam_pressure_bar",
                    type="number",
                    description="Operating steam pressure in bar (e.g. 16.0).",
                    required=True,
                ),
                ToolParameter(
                    name="feedwater_temp_c",
                    type="number",
                    description="Feedwater inlet temperature in °C (default: 105.0 °C with economizer/degasser).",
                    required=False,
                    default=105.0,
                ),
                ToolParameter(
                    name="fuel_type",
                    type="string",
                    description="Fuel type: 'natural_gas' (LHV ~34.5 MJ/m3), 'diesel' (LHV ~42.5 MJ/kg), or 'heavy_oil'.",
                    required=False,
                    default="natural_gas",
                ),
                ToolParameter(
                    name="boiler_efficiency_percent",
                    type="number",
                    description="Target boiler thermal efficiency in % (default: 91.5%).",
                    required=False,
                    default=91.5,
                ),
            ],
        )

    @classmethod
    async def execute(cls, arguments: Dict[str, Any]) -> Dict[str, Any]:
        steam_flow = float(arguments.get("steam_flow_kg_h", 1000.0))
        steam_pressure = float(arguments.get("steam_pressure_bar", 16.0))
        feedwater_temp = float(arguments.get("feedwater_temp_c", 105.0))
        fuel_type = str(arguments.get("fuel_type", "natural_gas")).lower()
        efficiency_pct = float(arguments.get("boiler_efficiency_percent", 91.5))

        # Enthalpy of saturated steam at given pressure (empirical approximation in kJ/kg)
        # Saturated steam at 16 bar has h ~ 2794 kJ/kg, at 10 bar ~ 2778 kJ/kg
        h_steam = 2700.0 + (5.5 * steam_pressure)  # kJ/kg
        # Enthalpy of liquid feedwater: h_fw = Cp * T ~ 4.186 * T (kJ/kg)
        h_fw = 4.186 * feedwater_temp  # kJ/kg

        delta_h = max(100.0, h_steam - h_fw)  # kJ/kg

        # Thermal Output: Q_dot = (m_dot_steam * delta_h) / 3600 -> kW
        thermal_output_kw = (steam_flow * delta_h) / 3600.0
        thermal_output_mw = thermal_output_kw / 1000.0

        # Fuel Lower Heating Values (LHV in MJ/unit)
        lhv_map = {
            "natural_gas": 34.5,  # MJ / Nm3
            "diesel": 42.5,       # MJ / kg
            "heavy_oil": 40.0,    # MJ / kg
        }
        lhv_mj = lhv_map.get(fuel_type, 34.5)

        # Total energy input required = Thermal Output / Efficiency
        efficiency_ratio = max(0.1, min(1.0, efficiency_pct / 100.0))
        energy_input_kw = thermal_output_kw / efficiency_ratio
        energy_input_mj_h = energy_input_kw * 3.6  # MJ/h

        # Fuel consumption rate = Energy Input / LHV
        fuel_consumption_rate = energy_input_mj_h / lhv_mj
        fuel_unit = "Nm3/h" if fuel_type == "natural_gas" else "kg/h"

        return {
            "steam_flow_kg_h": steam_flow,
            "steam_pressure_bar": steam_pressure,
            "feedwater_temp_c": feedwater_temp,
            "fuel_type": fuel_type,
            "efficiency_percent": efficiency_pct,
            "thermal_output_kw": round(thermal_output_kw, 2),
            "thermal_output_mw": round(thermal_output_mw, 3),
            "fuel_consumption_rate": round(fuel_consumption_rate, 2),
            "fuel_unit": fuel_unit,
            "formula_applied": "Q = m_steam * (h_steam - h_fw) / 3600, Fuel = Q / (eta * LHV)",
        }
