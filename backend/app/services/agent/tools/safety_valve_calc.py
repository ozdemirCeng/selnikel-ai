"""
Safety Relief Valve Sizing and Discharge Capacity Tool (EN ISO 4126-1 / ASME Section I).
Calculates minimum required discharge capacity (kg/h), flow orifice area (mm2),
and recommended valve nominal inlet/outlet diameters.
"""
import math
from typing import Any, Dict
from app.domain.agent import ToolDefinition, ToolParameter


class SafetyValveSizingTool:
    """Tool to calculate industrial steam boiler safety valve sizing according to EN ISO 4126-1 / ASME Section I."""

    @classmethod
    def get_definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="calculate_safety_valve_sizing",
            description="Calculates safety relief valve required discharge capacity (kg/h), minimum orifice area (mm2), and recommended nominal DN size (inlet/outlet) for steam boilers per EN ISO 4126-1 / ASME Sec I.",
            parameters=[
                ToolParameter(
                    name="boiler_capacity_kg_h",
                    type="number",
                    description="Maximum continuous boiler steam capacity (MCR) in kg/h (e.g. 5000.0).",
                    required=True,
                ),
                ToolParameter(
                    name="set_pressure_bar_g",
                    type="number",
                    description="Safety valve set pressure in bar gauge (e.g. 16.0 bar_g).",
                    required=True,
                ),
                ToolParameter(
                    name="overpressure_percent",
                    type="number",
                    description="Allowed overpressure percentage during discharge (default: 10.0% for steam per EN ISO 4126-1).",
                    required=False,
                    default=10.0,
                ),
                ToolParameter(
                    name="derated_discharge_coefficient",
                    type="number",
                    description="Certified derated coefficient of discharge Kdr (typical: 0.70 for full-lift steam valves).",
                    required=False,
                    default=0.70,
                ),
            ],
        )

    @classmethod
    async def execute(cls, arguments: Dict[str, Any]) -> Dict[str, Any]:
        capacity = float(arguments.get("boiler_capacity_kg_h", 5000.0))
        set_press_g = float(arguments.get("set_pressure_bar_g", 16.0))
        overpressure_pct = float(arguments.get("overpressure_percent", 10.0))
        kdr = float(arguments.get("derated_discharge_coefficient", 0.70))

        # 1. Relieving Absolute Pressure: P0 = (P_set * (1 + overpressure/100) + 1.013) bar_abs
        relieving_press_bar_abs = (set_press_g * (1.0 + overpressure_pct / 100.0)) + 1.01325
        p0_bar = relieving_press_bar_abs

        # 2. Saturated Steam Expansion Coefficient C (isentropic exponent k ~ 1.3 for steam)
        # C ~ 0.528 * sqrt(k * (2/(k+1))^((k+1)/(k-1))) ~ 2.45
        c_steam = 2.45

        # 3. Minimum Required Discharge Capacity (EN ISO 4126 / ASME I requires 100% or 110% of boiler MCR)
        required_discharge_kg_h = capacity * 1.0

        # 4. Minimum Discharge Orifice Area A0 (mm2)
        # Formula for dry saturated steam: A0 = q_m / (0.2883 * C * Kdr * P0_bar)
        # A0 in mm2, q_m in kg/h, P0 in bar_abs
        denominator = 0.2883 * c_steam * kdr * p0_bar
        orifice_area_mm2 = required_discharge_kg_h / max(0.1, denominator)
        orifice_diameter_mm = math.sqrt((4.0 * orifice_area_mm2) / math.pi)

        # 5. Standard Valve DN Mapping based on Orifice Diameter (EN 1092-1 / DIN 3320)
        if orifice_diameter_mm <= 15.0:
            dn_inlet, dn_outlet = 20, 32
        elif orifice_diameter_mm <= 23.0:
            dn_inlet, dn_outlet = 25, 40
        elif orifice_diameter_mm <= 30.0:
            dn_inlet, dn_outlet = 32, 50
        elif orifice_diameter_mm <= 38.0:
            dn_inlet, dn_outlet = 40, 65
        elif orifice_diameter_mm <= 47.0:
            dn_inlet, dn_outlet = 50, 80
        elif orifice_diameter_mm <= 60.0:
            dn_inlet, dn_outlet = 65, 100
        elif orifice_diameter_mm <= 75.0:
            dn_inlet, dn_outlet = 80, 125
        elif orifice_diameter_mm <= 95.0:
            dn_inlet, dn_outlet = 100, 150
        else:
            dn_inlet, dn_outlet = 125, 200

        valve_designation = f"DN {dn_inlet} / DN {dn_outlet} (Tam Kalkışlı / Full-Lift)"

        return {
            "boiler_capacity_kg_h": capacity,
            "set_pressure_bar_g": set_press_g,
            "relieving_pressure_bar_abs": round(p0_bar, 3),
            "derated_discharge_coefficient_kdr": kdr,
            "required_discharge_capacity_kg_h": round(required_discharge_kg_h, 1),
            "calculated_orifice_area_mm2": round(orifice_area_mm2, 1),
            "calculated_orifice_diameter_mm": round(orifice_diameter_mm, 1),
            "recommended_dn_inlet": dn_inlet,
            "recommended_dn_outlet": dn_outlet,
            "recommended_valve_size": valve_designation,
            "standards_compliance": "EN ISO 4126-1 & ASME Section I PG-67 / PG-70",
        }
