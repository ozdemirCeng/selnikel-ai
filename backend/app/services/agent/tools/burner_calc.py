"""
Burner Combustion and Flue Gas Loss Calculation Tool (ASME PTC 4.1 / EN 676).
Calculates stoichiometric & actual combustion air flow, flue gas loss (Siegert Formula),
excess air coefficient (lambda), and combustion efficiency.
"""
from typing import Any, Dict
from app.domain.agent import ToolDefinition, ToolParameter


class BurnerCombustionTool:
    """Tool to calculate industrial burner combustion parameters, air demand, and flue gas loss."""

    @classmethod
    def get_definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="calculate_burner_combustion",
            description="Calculates industrial burner air requirement (Nm3/h), excess air ratio (lambda), Siegert flue gas loss (%), and combustion efficiency (%) based on fuel consumption, fuel type, flue gas temperature, and residual O2/CO2.",
            parameters=[
                ToolParameter(
                    name="fuel_consumption_rate",
                    type="number",
                    description="Fuel consumption rate in fuel units (Nm3/h for gas, kg/h for liquid fuels).",
                    required=True,
                ),
                ToolParameter(
                    name="fuel_type",
                    type="string",
                    description="Fuel type: 'natural_gas', 'diesel', 'heavy_oil', or 'lpg'.",
                    required=False,
                    default="natural_gas",
                ),
                ToolParameter(
                    name="flue_gas_temp_c",
                    type="number",
                    description="Flue gas temperature at boiler exit in °C (e.g. 160.0).",
                    required=False,
                    default=160.0,
                ),
                ToolParameter(
                    name="ambient_temp_c",
                    type="number",
                    description="Combustion ambient air temperature in °C (default: 20.0 °C).",
                    required=False,
                    default=20.0,
                ),
                ToolParameter(
                    name="o2_dry_percent",
                    type="number",
                    description="Residual oxygen concentration in dry flue gas in % (e.g. 3.0% for natural gas, 4.0% for oil).",
                    required=False,
                    default=3.0,
                ),
            ],
        )

    @classmethod
    async def execute(cls, arguments: Dict[str, Any]) -> Dict[str, Any]:
        fuel_rate = float(arguments.get("fuel_consumption_rate", 100.0))
        fuel_type = str(arguments.get("fuel_type", "natural_gas")).lower()
        t_flue = float(arguments.get("flue_gas_temp_c", 160.0))
        t_amb = float(arguments.get("ambient_temp_c", 20.0))
        o2_pct = float(arguments.get("o2_dry_percent", 3.0))

        # Enforce bounds
        o2_pct = max(0.5, min(19.0, o2_pct))
        delta_t = max(10.0, t_flue - t_amb)

        # Stoichiometric air requirement (Nm3 air / unit fuel) & Siegert coefficients (A1, B)
        fuel_specs = {
            "natural_gas": {
                "v_air_min": 9.52,      # Nm3 air / Nm3 gas
                "v_flue_min": 10.50,    # Nm3 flue / Nm3 gas
                "co2_max": 11.8,        # % max CO2
                "siegert_a1": 0.38,     # Siegert A1 factor
                "siegert_b": 0.009,     # Siegert B factor
            },
            "diesel": {
                "v_air_min": 11.20,     # Nm3 air / kg diesel
                "v_flue_min": 12.10,    # Nm3 flue / kg diesel
                "co2_max": 15.4,        # % max CO2
                "siegert_a1": 0.49,
                "siegert_b": 0.007,
            },
            "heavy_oil": {
                "v_air_min": 10.80,
                "v_flue_min": 11.80,
                "co2_max": 15.8,
                "siegert_a1": 0.52,
                "siegert_b": 0.007,
            },
            "lpg": {
                "v_air_min": 24.50,
                "v_flue_min": 26.00,
                "co2_max": 13.8,
                "siegert_a1": 0.42,
                "siegert_b": 0.008,
            },
        }

        spec = fuel_specs.get(fuel_type, fuel_specs["natural_gas"])

        # 1. Excess Air Coefficient (lambda) calculated from O2
        # lambda = 21 / (21 - O2)
        excess_air_ratio = 21.0 / (21.0 - o2_pct)

        # 2. Calculated CO2 % in dry flue gas
        co2_dry_pct = spec["co2_max"] * (1.0 - (o2_pct / 21.0))

        # 3. Total combustion air flow rate (Nm3/h)
        total_air_flow_nm3_h = fuel_rate * spec["v_air_min"] * excess_air_ratio

        # 4. Total flue gas volume rate (Nm3/h at standard condition)
        # V_flue = V_flue_min + (lambda - 1) * V_air_min
        flue_gas_flow_nm3_h = fuel_rate * (spec["v_flue_min"] + (excess_air_ratio - 1.0) * spec["v_air_min"])

        # Operational flue gas volume rate at flue temperature (m3/h)
        # V_T = V_0 * (273.15 + T) / 273.15
        flue_gas_flow_actual_m3_h = flue_gas_flow_nm3_h * ((273.15 + t_flue) / 273.15)

        # 5. Siegert Flue Gas Loss Percentage (qA %)
        # qA = (T_flue - T_amb) * (A1 / CO2 + B)
        flue_gas_loss_pct = delta_t * ((spec["siegert_a1"] / max(0.5, co2_dry_pct)) + spec["siegert_b"])
        flue_gas_loss_pct = round(max(1.0, min(35.0, flue_gas_loss_pct)), 2)

        # 6. Combustion Efficiency % (DIN EN 676)
        combustion_efficiency_pct = round(100.0 - flue_gas_loss_pct, 2)

        return {
            "fuel_consumption_rate": fuel_rate,
            "fuel_type": fuel_type,
            "excess_air_ratio_lambda": round(excess_air_ratio, 3),
            "co2_dry_percent": round(co2_dry_pct, 2),
            "o2_dry_percent": round(o2_pct, 2),
            "flue_gas_temp_c": t_flue,
            "ambient_temp_c": t_amb,
            "delta_temp_c": round(delta_t, 1),
            "combustion_air_flow_nm3_h": round(total_air_flow_nm3_h, 2),
            "flue_gas_flow_nm3_h": round(flue_gas_flow_nm3_h, 2),
            "flue_gas_flow_actual_m3_h": round(flue_gas_flow_actual_m3_h, 2),
            "flue_gas_loss_percent": flue_gas_loss_pct,
            "combustion_efficiency_percent": combustion_efficiency_pct,
            "standard_applied": "EN 676 & ASME PTC 4.1 (Siegert Loss Formulation)",
        }
