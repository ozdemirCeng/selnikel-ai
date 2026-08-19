import math
from typing import Any, Dict
from app.domain.agent import ToolDefinition, ToolParameter


class FanAirflowTool:
    """Tool to calculate industrial fan airflow rate, dynamic pressure, and required motor power."""

    @classmethod
    def get_definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="calculate_fan_airflow",
            description="Calculates industrial radial/axial fan volumetric airflow rate (m3/h), air velocity (m/s), total pressure (Pa), and required shaft motor power (kW).",
            parameters=[
                ToolParameter(
                    name="duct_diameter_mm",
                    type="number",
                    description="Circular duct internal diameter in mm (e.g. 500 mm).",
                    required=True,
                ),
                ToolParameter(
                    name="air_velocity_m_s",
                    type="number",
                    description="Measured air velocity in m/s (e.g. 15.0 m/s).",
                    required=True,
                ),
                ToolParameter(
                    name="total_pressure_pa",
                    type="number",
                    description="Total fan static + dynamic pressure in Pascals (e.g. 1200 Pa).",
                    required=False,
                    default=1000.0,
                ),
                ToolParameter(
                    name="fan_efficiency_percent",
                    type="number",
                    description="Fan aerodynamic efficiency in % (default: 75.0%).",
                    required=False,
                    default=75.0,
                ),
            ],
        )

    @classmethod
    async def execute(cls, arguments: Dict[str, Any]) -> Dict[str, Any]:
        diameter_mm = float(arguments.get("duct_diameter_mm", 500.0))
        velocity = float(arguments.get("air_velocity_m_s", 15.0))
        total_pressure_pa = float(arguments.get("total_pressure_pa", 1000.0))
        fan_efficiency_pct = float(arguments.get("fan_efficiency_percent", 75.0))

        diameter_m = diameter_mm / 1000.0
        # Cross-sectional area: A = pi * (D / 2)^2
        area_m2 = math.pi * ((diameter_m / 2.0) ** 2)

        # Volumetric Flow Rate: Q = A * v (m3/s) -> m3/h
        flow_rate_m3_s = area_m2 * velocity
        flow_rate_m3_h = flow_rate_m3_s * 3600.0

        # Dynamic Pressure: P_dyn = 0.5 * rho * v^2 (rho_air = 1.204 kg/m3 at 20°C)
        rho_air = 1.204
        dynamic_pressure_pa = 0.5 * rho_air * (velocity**2)

        # Shaft Power: P_shaft = (Q_m3_s * P_total_pa) / (1000 * eta_fan)
        eta_ratio = max(0.1, min(1.0, fan_efficiency_pct / 100.0))
        shaft_power_kw = (flow_rate_m3_s * total_pressure_pa) / (1000.0 * eta_ratio)
        recommended_motor_kw = shaft_power_kw * 1.15  # 15% standard safety margin

        return {
            "duct_diameter_mm": diameter_mm,
            "duct_area_m2": round(area_m2, 4),
            "air_velocity_m_s": velocity,
            "flow_rate_m3_s": round(flow_rate_m3_s, 3),
            "flow_rate_m3_h": round(flow_rate_m3_h, 2),
            "dynamic_pressure_pa": round(dynamic_pressure_pa, 2),
            "total_pressure_pa": total_pressure_pa,
            "shaft_power_kw": round(shaft_power_kw, 2),
            "recommended_motor_power_kw": round(recommended_motor_kw, 2),
            "formula_applied": "Q = A * v * 3600, P_shaft = (Q * DeltaP) / (1000 * eta)",
        }
