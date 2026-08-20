"""
Script to generate synthetic industrial technical document fixtures
for Parser & Table Layout Fidelity verification (Stage P1.1).
Explicitly marked as synthetic_generated / unverified_draft.
"""
import hashlib
import json
from pathlib import Path
import docx
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors


def generate_pdf_fixture(output_path: Path):
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle("DocTitle", parent=styles["Heading1"], fontSize=18, leading=22)
    h2_style = ParagraphStyle("SectionH2", parent=styles["Heading2"], fontSize=13, leading=16)
    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, leading=13)

    # Page 1: General Specifications
    story.append(Paragraph("SELNIKEL ISITMA SISTEMLERI A.S.", title_style))
    story.append(Paragraph("SB-Series Industrial Steam Boiler Technical Datasheet", h2_style))
    story.append(Paragraph("Document Code: SB-DS-2026 | Revision: REV-02 | Department: Thermal Engineering", body_style))
    story.append(Spacer(1, 15))
    story.append(Paragraph("1. General Overview & Design Standards", h2_style))
    story.append(Paragraph(
        "The Selnikel SB-Series is a 3-pass scotch marine industrial fire-tube steam boiler designed in full compliance with EN 12953 and ASME Section I standards. High thermal efficiency is achieved through optimized flame-tube dimensions and integrated flue gas economizers.",
        body_style,
    ))
    story.append(Spacer(1, 20))
    story.append(PageBreak())

    # Page 2: Multi-Column Operating Parameters Table
    story.append(Paragraph("2. Technical Operating Parameters & Capacities", h2_style))
    story.append(Spacer(1, 10))

    table_data = [
        ["Model Code", "Steam Cap. (t/h)", "Working Press. (bar)", "Design Press. (bar)", "Steam Temp. (°C)", "Thermal Power (kW)"],
        ["SB-500", "0.5 t/h", "12.0 bar", "16.0 bar", "191.6 °C", "350 kW"],
        ["SB-1000", "1.0 t/h", "16.0 bar", "18.0 bar", "204.3 °C", "700 kW"],
        ["SB-2000", "2.0 t/h", "16.0 bar", "20.0 bar", "204.3 °C", "1400 kW"],
        ["SB-5000", "5.0 t/h", "16.0 bar", "25.0 bar", "204.3 °C", "3500 kW"],
    ]

    t = Table(table_data, colWidths=[80, 85, 95, 90, 85, 95])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1A365D")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
    ]))
    story.append(t)
    story.append(Spacer(1, 20))
    story.append(PageBreak())

    # Page 3: Safety & Relief Specifications
    story.append(Paragraph("3. Safety Relief Valves & Auxiliary Limits", h2_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Section 3.1: Safety relief valves must be configured with full discharge capacity at 10% overpressure. Set point for SB-Series safety valve 1 is strictly 16.5 bar, with nominal discharge rate of 1250 kg/h.",
        body_style,
    ))
    story.append(Spacer(1, 10))

    safety_table = [
        ["Safety Device", "Set Pressure (bar)", "Connection DN (mm)", "Discharge Cap. (kg/h)"],
        ["Primary Safety Valve", "16.5 bar", "32 mm", "1250 kg/h"],
        ["Secondary Safety Valve", "17.0 bar", "32 mm", "1300 kg/h"],
        ["High Pressure Switch", "16.2 bar", "15 mm", "N/A"],
    ]
    t2 = Table(safety_table, colWidths=[140, 110, 110, 140])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t2)

    doc.build(story)


def generate_docx_fixture(output_path: Path):
    doc = docx.Document()
    doc.add_heading("SELNIKEL MONOBLOCK INDUSTRIAL BURNERS", level=1)
    doc.add_paragraph("Service & Maintenance Operations Manual | Document ID: MB-OM-2026 | Revision: REV-01")

    doc.add_heading("1. Technical Air & Combustion Data", level=2)
    doc.add_paragraph("The combustion air blower operates at a nominal rotational speed of 2850 rpm with static air pressure of 45 mbar. Optimum flue gas O2 content must be maintained between 3.0% and 3.5%.")

    doc.add_heading("2. Periodic Maintenance Schedule & Intervals", level=2)
    doc.add_paragraph("Regular maintenance ensures emission compliance and prevents nozzle clogging:")

    table = doc.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Component"
    hdr_cells[1].text = "Inspection Action"
    hdr_cells[2].text = "Service Interval"
    hdr_cells[3].text = "Torque / Spec"

    maintenance_rows = [
        ("Burner Nozzles", "Clean and inspect spray pattern", "500 hour", "25 Nm"),
        ("Ignition Electrodes", "Check spark gap (3.0 mm)", "1000 hour", "3.0 mm gap"),
        ("Flame Sensor Photocell", "Clean optical glass surface", "1000 hour", "Clean room spec"),
        ("Gas Valve Train", "Tightness and leak test", "6 month", "No bubble at 100 mbar"),
        ("Complete Blower Overhaul", "Bearing lubrication and dynamic balancing", "1 year", "ISO 1940 G2.5"),
    ]

    for comp, act, interv, spec in maintenance_rows:
        row_cells = table.add_row().cells
        row_cells[0].text = comp
        row_cells[1].text = act
        row_cells[2].text = interv
        row_cells[3].text = spec

    doc.add_paragraph("Note: Replacement parts must be OEM certified to preserve warranty conditions.")
    doc.save(str(output_path))


def generate_complex_multipage_docx_fixture(output_path: Path):
    """Generates a 2-page complex DOCX with page break, multi-line cells, and pipe characters."""
    doc = docx.Document()

    # Page 1
    doc.add_heading("SELNIKEL COMMISSIONING & TOLERANCE GUIDE", level=1)
    doc.add_paragraph("Document: CG-2026-V1 | Department: Field Service")
    doc.add_heading("1. Pre-Commissioning Electrical Limits", level=2)
    doc.add_paragraph("Verify 3-phase supply voltage: 400 V +/- 10% at 50 Hz.")

    table1 = doc.add_table(rows=1, cols=3)
    table1.style = "Table Grid"
    t1_hdr = table1.rows[0].cells
    t1_hdr[0].text = "Terminal"
    t1_hdr[1].text = "Signal Type"
    t1_hdr[2].text = "Allowed Range"

    t1_rows = [
        ("L1-L2-L3", "Main Power", "380 - 420 V"),
        ("T1-T2", "PT100 Sensor", "0 - 300 °C"),
        ("P1-P2", "Pressure 4-20 mA", "0.0 - 25.0 bar"),
    ]
    for r in t1_rows:
        rc = table1.add_row().cells
        rc[0].text = r[0]
        rc[1].text = r[1]
        rc[2].text = r[2]

    doc.add_page_break()

    # Page 2
    doc.add_heading("2. Flue Gas Emission Limits", level=2)
    doc.add_paragraph("Measured at nominal capacity under dry flue gas conditions:")

    table2 = doc.add_table(rows=1, cols=3)
    table2.style = "Table Grid"
    t2_hdr = table2.rows[0].cells
    t2_hdr[0].text = "Emission Parameter"
    t2_hdr[1].text = "Natural Gas Limit"
    t2_hdr[2].text = "Light Oil Limit"

    t2_rows = [
        ("CO Concentration", "< 50 mg/Nm³", "< 80 mg/Nm³"),
        ("NOx Class III", "< 100 mg/kWh", "< 150 mg/kWh"),
        ("Flue Temp (Net)", "160 - 180 °C", "180 - 210 °C"),
    ]
    for r in t2_rows:
        rc = table2.add_row().cells
        rc[0].text = r[0]
        rc[1].text = r[1]
        rc[2].text = r[2]

    doc.save(str(output_path))


def generate_txt_fixture(output_path: Path):
    content = """# SELNIKEL THERMAL OIL HEATERS
Document: TOH-SPEC-2026 | Revision: REV-03 | Department: Project Engineering

## 1. Operating Fluid & Temperature Limits
Thermal oil heaters are designed for closed-loop thermal fluid systems utilizing synthetic or mineral heat transfer oils.

### Table: Thermal Oil Operational Limits
| Parameter | Minimum Value | Nominal Value | Maximum Safety Limit | Unit |
| :--- | :--- | :--- | :--- | :--- |
| Flow Temperature | 180 °C | 280 °C | 320 °C | °C |
| Return Temperature | 150 °C | 240 °C | 290 °C | °C |
| System Operating Pressure | 2.5 bar | 4.0 bar | 6.0 bar | bar |
| Minimum Circulating Flow | 25 m³/h | 45 m³/h | 80 m³/h | m³/h |
| Expansion Tank Pre-charge | 0.5 bar | 1.0 bar | 1.5 bar | bar |

## 2. Safety Interlocks
If thermal fluid circulation drops below 25 m³/h, the burner controller must trigger an emergency lockout within 2.0 seconds.
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)


def compute_sha256(file_path: Path) -> str:
    with open(file_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main():
    fixtures_dir = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "documents"
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    pdf_path = fixtures_dir / "SB_Series_Steam_Boiler_Datasheet.pdf"
    docx_path = fixtures_dir / "Monoblock_Burner_Maintenance_Manual.docx"
    complex_docx_path = fixtures_dir / "Industrial_Boiler_Commissioning_Guide.docx"
    txt_path = fixtures_dir / "Thermal_Oil_Heater_Operating_Limits.txt"

    print("[*] Generating synthetic PDF technical datasheet fixture...")
    generate_pdf_fixture(pdf_path)

    print("[*] Generating synthetic DOCX maintenance manual fixture...")
    generate_docx_fixture(docx_path)

    print("[*] Generating synthetic multi-page DOCX commissioning guide fixture...")
    generate_complex_multipage_docx_fixture(complex_docx_path)

    print("[*] Generating synthetic TXT/MD operating limits fixture...")
    generate_txt_fixture(txt_path)

    manifest = {
        "manifest_version": "1.1.0",
        "description": "Selnikel AI Synthetically Generated Industrial Technical Document Fixtures Inventory for Stage P1.1",
        "fixture_kind": "synthetic_generated",
        "synthetic": True,
        "review_status": "unverified_draft",
        "generator": "backend/scripts/generate_fixtures.py",
        "fixtures": [
            {
                "filename": pdf_path.name,
                "relative_path": f"tests/fixtures/documents/{pdf_path.name}",
                "format": "pdf",
                "sha256": compute_sha256(pdf_path),
                "page_count": 3,
                "revision_code": "REV-02",
                "ocr_applied": False,
                "section_inventory": [
                    {"page_number": 1, "header": "1. General Overview & Design Standards"},
                    {"page_number": 2, "header": "2. Technical Operating Parameters & Capacities"},
                    {"page_number": 3, "header": "3. Safety Relief Valves & Auxiliary Limits"}
                ],
                "table_inventory": [
                    {
                        "table_id": "pdf_tab_01",
                        "page_number": 2,
                        "title": "Technical Operating Parameters & Capacities",
                        "column_count": 6,
                        "row_count": 4,
                        "headers": ["Model Code", "Steam Cap. (t/h)", "Working Press. (bar)", "Design Press. (bar)", "Steam Temp. (°C)", "Thermal Power (kW)"],
                        "ground_truth_cells": {
                            "SB-500": {"steam_cap": "0.5 t/h", "working_press": "12.0 bar", "design_press": "16.0 bar", "steam_temp": "191.6 °C", "thermal_power": "350 kW"},
                            "SB-1000": {"steam_cap": "1.0 t/h", "working_press": "16.0 bar", "design_press": "18.0 bar", "steam_temp": "204.3 °C", "thermal_power": "700 kW"},
                            "SB-2000": {"steam_cap": "2.0 t/h", "working_press": "16.0 bar", "design_press": "20.0 bar", "steam_temp": "204.3 °C", "thermal_power": "1400 kW"},
                            "SB-5000": {"steam_cap": "5.0 t/h", "working_press": "16.0 bar", "design_press": "25.0 bar", "steam_temp": "204.3 °C", "thermal_power": "3500 kW"}
                        }
                    },
                    {
                        "table_id": "pdf_tab_02",
                        "page_number": 3,
                        "title": "Safety Relief Valves & Auxiliary Limits",
                        "column_count": 4,
                        "row_count": 3,
                        "headers": ["Safety Device", "Set Pressure (bar)", "Connection DN (mm)", "Discharge Cap. (kg/h)"],
                        "ground_truth_cells": {
                            "Primary Safety Valve": {"set_pressure": "16.5 bar", "dn": "32 mm", "discharge_cap": "1250 kg/h"}
                        }
                    }
                ]
            },
            {
                "filename": docx_path.name,
                "relative_path": f"tests/fixtures/documents/{docx_path.name}",
                "format": "docx",
                "sha256": compute_sha256(docx_path),
                "page_count": 1,
                "revision_code": "REV-01",
                "ocr_applied": False,
                "section_inventory": [
                    {"page_number": 1, "header": "1. Technical Air & Combustion Data"},
                    {"page_number": 1, "header": "2. Periodic Maintenance Schedule & Intervals"}
                ],
                "table_inventory": [
                    {
                        "table_id": "docx_tab_01",
                        "page_number": 1,
                        "title": "Periodic Maintenance Schedule & Intervals",
                        "column_count": 4,
                        "row_count": 5,
                        "headers": ["Component", "Inspection Action", "Service Interval", "Torque / Spec"],
                        "ground_truth_cells": {
                            "Burner Nozzles": {"action": "Clean and inspect spray pattern", "interval": "500 hour", "torque": "25 Nm"},
                            "Gas Valve Train": {"action": "Tightness and leak test", "interval": "6 month", "torque": "No bubble at 100 mbar"},
                            "Complete Blower Overhaul": {"action": "Bearing lubrication and dynamic balancing", "interval": "1 year", "torque": "ISO 1940 G2.5"}
                        }
                    }
                ]
            },
            {
                "filename": complex_docx_path.name,
                "relative_path": f"tests/fixtures/documents/{complex_docx_path.name}",
                "format": "docx",
                "sha256": compute_sha256(complex_docx_path),
                "page_count": 2,
                "revision_code": "REV-01",
                "ocr_applied": False,
                "section_inventory": [
                    {"page_number": 1, "header": "1. Pre-Commissioning Electrical Limits"},
                    {"page_number": 2, "header": "2. Flue Gas Emission Limits"}
                ],
                "table_inventory": [
                    {
                        "table_id": "docx_tab_01",
                        "page_number": 1,
                        "title": "Pre-Commissioning Electrical Limits",
                        "column_count": 3,
                        "row_count": 3,
                        "headers": ["Terminal", "Signal Type", "Allowed Range"],
                        "ground_truth_cells": {
                            "L1-L2-L3": {"signal": "Main Power", "range": "380 - 420 V"},
                            "P1-P2": {"signal": "Pressure 4-20 mA", "range": "0.0 - 25.0 bar"}
                        }
                    },
                    {
                        "table_id": "docx_tab_02",
                        "page_number": 2,
                        "title": "Flue Gas Emission Limits",
                        "column_count": 3,
                        "row_count": 3,
                        "headers": ["Emission Parameter", "Natural Gas Limit", "Light Oil Limit"],
                        "ground_truth_cells": {
                            "CO Concentration": {"ng": "< 50 mg/Nm³", "oil": "< 80 mg/Nm³"},
                            "NOx Class III": {"ng": "< 100 mg/kWh", "oil": "< 150 mg/kWh"}
                        }
                    }
                ]
            },
            {
                "filename": txt_path.name,
                "relative_path": f"tests/fixtures/documents/{txt_path.name}",
                "format": "txt",
                "sha256": compute_sha256(txt_path),
                "page_count": 1,
                "revision_code": "REV-03",
                "ocr_applied": False,
                "section_inventory": [
                    {"page_number": 1, "header": "1. Operating Fluid & Temperature Limits"},
                    {"page_number": 1, "header": "2. Safety Interlocks"}
                ],
                "table_inventory": [
                    {
                        "table_id": "txt_tab_01",
                        "page_number": 1,
                        "title": "Thermal Oil Operational Limits",
                        "column_count": 5,
                        "row_count": 5,
                        "headers": ["Parameter", "Minimum Value", "Nominal Value", "Maximum Safety Limit", "Unit"],
                        "ground_truth_cells": {
                            "Flow Temperature": {"min": "180 °C", "nom": "280 °C", "max": "320 °C"},
                            "System Operating Pressure": {"min": "2.5 bar", "nom": "4.0 bar", "max": "6.0 bar"},
                            "Minimum Circulating Flow": {"min": "25 m³/h", "nom": "45 m³/h", "max": "80 m³/h"}
                        }
                    }
                ]
            }
        ]
    }

    manifest_path = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "fixture_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=2, ensure_ascii=False)

    print(f"[+] Successfully generated 4 synthetic fixtures and saved manifest to {manifest_path}")


if __name__ == "__main__":
    main()
