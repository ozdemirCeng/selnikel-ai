"""
Economizer and Waste Heat Recovery Calculation Tool (EN 12952 / ASME Section I).
Calculates recovered thermal power (kW), feedwater temperature rise, annual fuel savings,
and boiler thermal efficiency gain.
"""
from typing import Any, Dict
from app.domain.agent import ToolDefinition, ToolParameter


class EconomizerHeatRecoveryTool:
    """Tool to calculate industrial boiler economizer waste heat recovery and energy savings."""

    @classmethod
    def get_definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="calculate_economizer_recovery",
            description="Calculates waste heat recovery from boiler flue gas (kW/MW), feedwater preheating delta T (°C), annual fuel savings (Nm3/year or kg/year), and efficiency boost (%) provided by an economizer.",
            parameters=[
                ToolParameter(
                    name="steam_flow_kg_h",
                    type="number",
                    description="Boiler feedwater / steam flow rate in kg/h (e.g. 5000.0).",
                    required=True,
                ),
                ToolParameter(
                    name="flue_gas_inlet_temp_c",
                    type="number",
                    description="Flue gas temperature entering economizer in °C (e.g. 220.0).",
                    required=False,
                    default=220.0,
                ),
                ToolParameter(
                    name="flue_gas_outlet_temp_c",
                    type="number",
                    description="Target flue gas temperature exiting economizer in °C (e.g. 130.0).",
                    required=False,
                    default=130.0,
                ),
                ToolParameter(
                    name="feedwater_inlet_temp_c",
                    type="number",
                    description="Feedwater inlet temperature to economizer in °C (e.g. 85.0).",
                    required=False,
                    default=85.0,
                ),
                ToolParameter(
                    name="operating_hours_per_year",
                    type="number",
                    description="Annual operating hours of the plant (default: 6000 hours/year).",
                    required=False,
                    default=6000.0,
                ),
                ToolParameter(
                    name="fuel_type",
                    type="string",
                    description="Fuel type: 'natural_gas', 'diesel', or 'heavy_oil'.",
                    required=False,
                    default="natural_gas",
                ),
            ],
        )

    @classmethod
    async def execute(cls, arguments: Dict[str, Any]) -> Dict[str, Any]:
        steam_flow = float(arguments.get("steam_flow_kg_h", 5000.0))
        t_flue_in = float(arguments.get("flue_gas_inlet_temp_c", 220.0))
        t_flue_out = float(arguments.get("flue_gas_outlet_temp_c", 130.0))
        t_fw_in = float(arguments.get("feedwater_inlet_temp_c", 85.0))
        op_hours = float(arguments.get("operating_hours_per_year", 6000.0))
        fuel_type = str(arguments.get("fuel_type", "natural_gas")).lower()

        # Enforce valid temperature differential
        delta_t_flue = max(10.0, t_flue_in - t_flue_out)

        # Flue gas generation ratio per kg steam (empirical average for natural gas / oil ~ 1.35 kg flue gas / kg steam)
        m_flue_kg_h = steam_flow * 1.35
        # Specific heat capacity of flue gas Cp ~ 1.08 kJ/kg.K
        cp_flue = 1.08  # kJ/kg.K
        # Specific heat capacity of water Cp ~ 4.186 kJ/kg.K
        cp_water = 4.186  # kJ/kg.K

        # 1. Recovered Thermal Power: Q_rec = (m_flue * Cp_flue * delta_T_flue) / 3600 -> kW
        recovered_power_kw = (m_flue_kg_h * cp_flue * delta_t_flue) / 3600.0
        recovered_power_mw = recovered_power_kw / 1000.0

        # 2. Feedwater Temperature Rise: delta_T_fw = (Q_rec * 3600) / (m_fw * Cp_water)
        delta_t_fw = (recovered_power_kw * 3600.0) / (max(10.0, steam_flow) * cp_water)
        t_fw_out = t_fw_in + delta_t_fw

        # 3. Efficiency Boost: approx 1% efficiency increase per 20 °C flue gas drop
        efficiency_gain_pct = round(delta_t_flue / 20.0, 2)

        # 4. Annual Energy Saved: kWh and MJ
        annual_energy_kwh = recovered_power_kw * op_hours
        annual_energy_mj = annual_energy_kwh * 3.6

        # 5. Annual Fuel Savings
        lhv_map = {
            "natural_gas": 34.5,  # MJ / Nm3
            "diesel": 42.5,       # MJ / kg
            "heavy_oil": 40.0,    # MJ / kg
        }
        lhv_mj = lhv_map.get(fuel_type, 34.5)
        annual_fuel_saved = annual_energy_mj / lhv_mj
        fuel_unit = "Nm3/yıl" if fuel_type == "natural_gas" else "kg/yıl"

        return {
            "steam_flow_kg_h": steam_flow,
            "flue_gas_inlet_temp_c": t_flue_in,
            "flue_gas_outlet_temp_c": t_flue_out,
            "flue_gas_temp_drop_c": round(delta_t_flue, 1),
            "feedwater_inlet_temp_c": t_fw_in,
            "feedwater_outlet_temp_c": round(t_fw_out, 1),
            "feedwater_temp_rise_c": round(delta_t_fw, 1),
            "recovered_power_kw": round(recovered_power_kw, 2),
            "recovered_power_mw": round(recovered_power_mw, 3),
            "efficiency_gain_percent": efficiency_gain_pct,
            "annual_operating_hours": op_hours,
            "annual_energy_saved_mwh": round(annual_energy_kwh / 1000.0, 2),
            "annual_fuel_savings": round(annual_fuel_saved, 1),
            "fuel_unit": fuel_unit,
            "standard_basis": "EN 12952-15 Economizer Thermal Performance Sizing",
        }
