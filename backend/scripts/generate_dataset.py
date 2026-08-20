import json
from pathlib import Path

MANIFEST_PATH = Path('backend/tests/fixtures/fixture_manifest.json')
DATASET_PATH = Path('backend/app/evaluation/datasets/golden_benchmark_v1.json')
DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)

with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
    manifest = json.load(f)

hashes = {fix['filename']: fix['sha256'] for fix in manifest['fixtures']}

dataset = [
  {
    "id": "selnikel-bench-001",
    "category": "capacity_pressure_temp",
    "question": "What is the steam capacity and design pressure for the Selnikel SB-500 boiler model according to the technical datasheet?",
    "expected_evidence": {
      "document_name": "SB_Series_Steam_Boiler_Datasheet.pdf",
      "document_sha256": hashes["SB_Series_Steam_Boiler_Datasheet.pdf"],
      "revision_code": "REV-02",
      "page_number": 2,
      "section": "2. Technical Operating Parameters & Capacities",
      "locator": {
        "locator_type": "table_cell",
        "table_id": "pdf_tab_01",
        "row_key": "SB-500",
        "column_name": "design_press"
      },
      "expected_numerical_parameters": ["0.5 t/h", "16.0 bar"],
      "ground_truth_answer": "The SB-500 steam boiler has a steam capacity of 0.5 t/h and a design pressure of 16.0 bar."
    },
    "is_safety_critical": False,
    "is_out_of_domain": False,
    "dataset_version": "1.0.0",
    "synthetic": True,
    "review_status": "unverified_draft"
  },
  {
    "id": "selnikel-bench-002",
    "category": "capacity_pressure_temp",
    "question": "What is the operating steam temperature and thermal power rating for model SB-1000?",
    "expected_evidence": {
      "document_name": "SB_Series_Steam_Boiler_Datasheet.pdf",
      "document_sha256": hashes["SB_Series_Steam_Boiler_Datasheet.pdf"],
      "revision_code": "REV-02",
      "page_number": 2,
      "section": "2. Technical Operating Parameters & Capacities",
      "locator": {
        "locator_type": "table_cell",
        "table_id": "pdf_tab_01",
        "row_key": "SB-1000",
        "column_name": "steam_temp"
      },
      "expected_numerical_parameters": ["204.3 °C", "700 kW"],
      "ground_truth_answer": "Model SB-1000 provides a steam temperature of 204.3 °C and thermal power rating of 700 kW."
    },
    "is_safety_critical": False,
    "is_out_of_domain": False,
    "dataset_version": "1.0.0",
    "synthetic": True,
    "review_status": "unverified_draft"
  },
  {
    "id": "selnikel-bench-003",
    "category": "capacity_pressure_temp",
    "question": "For the SB-5000 industrial boiler, what are the working pressure and design pressure limits?",
    "expected_evidence": {
      "document_name": "SB_Series_Steam_Boiler_Datasheet.pdf",
      "document_sha256": hashes["SB_Series_Steam_Boiler_Datasheet.pdf"],
      "revision_code": "REV-02",
      "page_number": 2,
      "section": "2. Technical Operating Parameters & Capacities",
      "locator": {
        "locator_type": "table_cell",
        "table_id": "pdf_tab_01",
        "row_key": "SB-5000",
        "column_name": "working_press"
      },
      "expected_numerical_parameters": ["16.0 bar", "25.0 bar"],
      "ground_truth_answer": "The SB-5000 operates at a working pressure of 16.0 bar and a maximum design pressure of 25.0 bar."
    },
    "is_safety_critical": False,
    "is_out_of_domain": False,
    "dataset_version": "1.0.0",
    "synthetic": True,
    "review_status": "unverified_draft"
  },
  {
    "id": "selnikel-bench-004",
    "category": "maintenance_intervals",
    "question": "How often should the burner nozzles be cleaned and inspected on Monoblock MB-Series burners?",
    "expected_evidence": {
      "document_name": "Monoblock_Burner_Maintenance_Manual.docx",
      "document_sha256": hashes["Monoblock_Burner_Maintenance_Manual.docx"],
      "revision_code": "REV-01",
      "page_number": 1,
      "section": "2. Periodic Maintenance Schedule & Intervals",
      "locator": {
        "locator_type": "table_cell",
        "table_id": "docx_tab_01",
        "row_key": "Burner Nozzles",
        "column_name": "interval"
      },
      "expected_numerical_parameters": ["500 hour", "25 Nm"],
      "ground_truth_answer": "Burner nozzles must be cleaned and inspected every 500 hours with a tightening torque of 25 Nm."
    },
    "is_safety_critical": False,
    "is_out_of_domain": False,
    "dataset_version": "1.0.0",
    "synthetic": True,
    "review_status": "unverified_draft"
  },
  {
    "id": "selnikel-bench-005",
    "category": "maintenance_intervals",
    "question": "What is the service interval and action required for a complete nozzle overhaul?",
    "expected_evidence": {
      "document_name": "Monoblock_Burner_Maintenance_Manual.docx",
      "document_sha256": hashes["Monoblock_Burner_Maintenance_Manual.docx"],
      "revision_code": "REV-01",
      "page_number": 1,
      "section": "2. Periodic Maintenance Schedule & Intervals",
      "locator": {
        "locator_type": "table_cell",
        "table_id": "docx_tab_01",
        "row_key": "Nozzle Overhaul",
        "column_name": "interval"
      },
      "expected_numerical_parameters": ["2000 hour", "30 Nm"],
      "ground_truth_answer": "Nozzle overhaul requires replacing the atomizing disc and filter every 2000 hours with 30 Nm torque."
    },
    "is_safety_critical": False,
    "is_out_of_domain": False,
    "dataset_version": "1.0.0",
    "synthetic": True,
    "review_status": "unverified_draft"
  },
  {
    "id": "selnikel-bench-006",
    "category": "maintenance_intervals",
    "question": "What are the periodic inspection requirements and interval for the gas valve train tightness test?",
    "expected_evidence": {
      "document_name": "Monoblock_Burner_Maintenance_Manual.docx",
      "document_sha256": hashes["Monoblock_Burner_Maintenance_Manual.docx"],
      "revision_code": "REV-01",
      "page_number": 1,
      "section": "2. Periodic Maintenance Schedule & Intervals",
      "locator": {
        "locator_type": "table_cell",
        "table_id": "docx_tab_01",
        "row_key": "Gas Valve Train",
        "column_name": "interval"
      },
      "expected_numerical_parameters": ["6 month"],
      "ground_truth_answer": "Gas valve train tightness and leak testing must be performed every 6 months ensuring no bubbles at 100 mbar."
    },
    "is_safety_critical": False,
    "is_out_of_domain": False,
    "dataset_version": "1.0.0",
    "synthetic": True,
    "review_status": "unverified_draft"
  },
  {
    "id": "selnikel-bench-007",
    "category": "fault_troubleshooting",
    "question": "What does fault code E01 indicate on MB-Series burners and what corrective action is required?",
    "expected_evidence": {
      "document_name": "Monoblock_Burner_Maintenance_Manual.docx",
      "document_sha256": hashes["Monoblock_Burner_Maintenance_Manual.docx"],
      "revision_code": "REV-01",
      "page_number": 2,
      "section": "3. Diagnostic Fault Codes & Troubleshooting Matrix",
      "locator": {
        "locator_type": "table_cell",
        "table_id": "docx_tab_02",
        "row_key": "E01",
        "column_name": "desc"
      },
      "expected_numerical_parameters": [],
      "ground_truth_answer": "Fault code E01 indicates Flame Failure Lockout due to ionization probe contamination or gas cutoff; clean the ionization probe and verify supply pressure."
    },
    "is_safety_critical": False,
    "is_out_of_domain": False,
    "dataset_version": "1.0.0",
    "synthetic": True,
    "review_status": "unverified_draft"
  },
  {
    "id": "selnikel-bench-008",
    "category": "fault_troubleshooting",
    "question": "What is the cause and recommended action for diagnostic fault code E04?",
    "expected_evidence": {
      "document_name": "Monoblock_Burner_Maintenance_Manual.docx",
      "document_sha256": hashes["Monoblock_Burner_Maintenance_Manual.docx"],
      "revision_code": "REV-01",
      "page_number": 2,
      "section": "3. Diagnostic Fault Codes & Troubleshooting Matrix",
      "locator": {
        "locator_type": "table_cell",
        "table_id": "docx_tab_02",
        "row_key": "E04",
        "column_name": "cause"
      },
      "expected_numerical_parameters": [],
      "ground_truth_answer": "Fault code E04 represents an Air Pressure Switch Fault caused by insufficient combustion air flow or clogged fan; check blower differential pressure and air switch tube."
    },
    "is_safety_critical": False,
    "is_out_of_domain": False,
    "dataset_version": "1.0.0",
    "synthetic": True,
    "review_status": "unverified_draft"
  },
  {
    "id": "selnikel-bench-009",
    "category": "fault_troubleshooting",
    "question": "What fault is indicated by code E07 on the burner control unit and how should it be resolved?",
    "expected_evidence": {
      "document_name": "Monoblock_Burner_Maintenance_Manual.docx",
      "document_sha256": hashes["Monoblock_Burner_Maintenance_Manual.docx"],
      "revision_code": "REV-01",
      "page_number": 2,
      "section": "3. Diagnostic Fault Codes & Troubleshooting Matrix",
      "locator": {
        "locator_type": "table_cell",
        "table_id": "docx_tab_02",
        "row_key": "E07",
        "column_name": "action"
      },
      "expected_numerical_parameters": [],
      "ground_truth_answer": "Code E07 indicates High Flue Gas Temperature Trip caused by soot buildup in the heat exchanger; shutdown burner and perform boiler tube cleaning."
    },
    "is_safety_critical": False,
    "is_out_of_domain": False,
    "dataset_version": "1.0.0",
    "synthetic": True,
    "review_status": "unverified_draft"
  },
  {
    "id": "selnikel-bench-010",
    "category": "parts_compatibility",
    "question": "What is the thread specification for replacement burner nozzles on MB-Series monoblock burners?",
    "expected_evidence": {
      "document_name": "Monoblock_Burner_Maintenance_Manual.docx",
      "document_sha256": hashes["Monoblock_Burner_Maintenance_Manual.docx"],
      "revision_code": "REV-01",
      "page_number": 2,
      "section": "4. Burner Nozzle & Mechanical Parts Compatibility",
      "locator": {
        "locator_type": "section_text",
        "section_header": "4. Burner Nozzle & Mechanical Parts Compatibility",
        "key_phrase": "9/16-24 UNEF"
      },
      "expected_numerical_parameters": [],
      "ground_truth_answer": "Replacement burner nozzles must comply with 9/16-24 UNEF standard thread specification."
    },
    "is_safety_critical": False,
    "is_out_of_domain": False,
    "dataset_version": "1.0.0",
    "synthetic": True,
    "review_status": "unverified_draft"
  },
  {
    "id": "selnikel-bench-011",
    "category": "parts_compatibility",
    "question": "What is the nominal connection size (DN) and discharge capacity for the primary safety relief valve on SB-Series boilers?",
    "expected_evidence": {
      "document_name": "SB_Series_Steam_Boiler_Datasheet.pdf",
      "document_sha256": hashes["SB_Series_Steam_Boiler_Datasheet.pdf"],
      "revision_code": "REV-02",
      "page_number": 3,
      "section": "3. Safety Relief Valves & Auxiliary Limits",
      "locator": {
        "locator_type": "table_cell",
        "table_id": "pdf_tab_02",
        "row_key": "Primary Safety Valve",
        "column_name": "dn"
      },
      "expected_numerical_parameters": ["32 mm", "1250 kg/h"],
      "ground_truth_answer": "The primary safety relief valve has a nominal connection size of DN 32 mm and a discharge capacity of 1250 kg/h."
    },
    "is_safety_critical": False,
    "is_out_of_domain": False,
    "dataset_version": "1.0.0",
    "synthetic": True,
    "review_status": "unverified_draft"
  },
  {
    "id": "selnikel-bench-012",
    "category": "parts_compatibility",
    "question": "What are the gas inlet flange connection and filter mesh ratings for Monoblock burners?",
    "expected_evidence": {
      "document_name": "Monoblock_Burner_Maintenance_Manual.docx",
      "document_sha256": hashes["Monoblock_Burner_Maintenance_Manual.docx"],
      "revision_code": "REV-01",
      "page_number": 2,
      "section": "4. Burner Nozzle & Mechanical Parts Compatibility",
      "locator": {
        "locator_type": "section_text",
        "section_header": "4. Burner Nozzle & Mechanical Parts Compatibility",
        "key_phrase": "100 microns"
      },
      "expected_numerical_parameters": ["100 microns"],
      "ground_truth_answer": "MB-Series burners use a DN65 PN16 gas flange interface and 100 microns rated stainless steel filter mesh."
    },
    "is_safety_critical": False,
    "is_out_of_domain": False,
    "dataset_version": "1.0.0",
    "synthetic": True,
    "review_status": "unverified_draft"
  },
  {
    "id": "selnikel-bench-013",
    "category": "standards_compliance",
    "question": "Which European standard governs the design, manufacturing, and safety requirements of Selnikel shell boilers?",
    "expected_evidence": {
      "document_name": "Industrial_Boiler_Commissioning_Guide.docx",
      "document_sha256": hashes["Industrial_Boiler_Commissioning_Guide.docx"],
      "revision_code": "REV-01",
      "page_number": 1,
      "section": "2. Standards, Directives & Regulatory Compliance",
      "locator": {
        "locator_type": "section_text",
        "section_header": "2. Standards, Directives & Regulatory Compliance",
        "key_phrase": "EN 12953"
      },
      "expected_numerical_parameters": [],
      "ground_truth_answer": "Selnikel shell boilers comply with European harmonized standard EN 12953."
    },
    "is_safety_critical": False,
    "is_out_of_domain": False,
    "dataset_version": "1.0.0",
    "synthetic": True,
    "review_status": "unverified_draft"
  },
  {
    "id": "selnikel-bench-014",
    "category": "standards_compliance",
    "question": "What Pressure Equipment Directive conformity module and category applies to the industrial boiler commissioning guide?",
    "expected_evidence": {
      "document_name": "Industrial_Boiler_Commissioning_Guide.docx",
      "document_sha256": hashes["Industrial_Boiler_Commissioning_Guide.docx"],
      "revision_code": "REV-01",
      "page_number": 1,
      "section": "2. Standards, Directives & Regulatory Compliance",
      "locator": {
        "locator_type": "section_text",
        "section_header": "2. Standards, Directives & Regulatory Compliance",
        "key_phrase": "PED 2014/68/EU"
      },
      "expected_numerical_parameters": [],
      "ground_truth_answer": "Boilers adhere to Pressure Equipment Directive PED 2014/68/EU Category IV under module H1 certification."
    },
    "is_safety_critical": False,
    "is_out_of_domain": False,
    "dataset_version": "1.0.0",
    "synthetic": True,
    "review_status": "unverified_draft"
  },
  {
    "id": "selnikel-bench-015",
    "category": "standards_compliance",
    "question": "Which European standard regulates automatic forced draught burners for gaseous fuels in Selnikel systems?",
    "expected_evidence": {
      "document_name": "Industrial_Boiler_Commissioning_Guide.docx",
      "document_sha256": hashes["Industrial_Boiler_Commissioning_Guide.docx"],
      "revision_code": "REV-01",
      "page_number": 1,
      "section": "2. Standards, Directives & Regulatory Compliance",
      "locator": {
        "locator_type": "section_text",
        "section_header": "2. Standards, Directives & Regulatory Compliance",
        "key_phrase": "EN 676"
      },
      "expected_numerical_parameters": [],
      "ground_truth_answer": "Automatic forced draught gas burners are regulated by European standard EN 676."
    },
    "is_safety_critical": False,
    "is_out_of_domain": False,
    "dataset_version": "1.0.0",
    "synthetic": True,
    "review_status": "unverified_draft"
  },
  {
    "id": "selnikel-bench-016",
    "category": "revision_conflicts",
    "question": "What was the design pressure for model SB-500 in baseline revision REV-01 compared to current REV-02?",
    "expected_evidence": {
      "document_name": "SB_Series_Steam_Boiler_Datasheet_REV01.pdf",
      "document_sha256": hashes["SB_Series_Steam_Boiler_Datasheet_REV01.pdf"],
      "revision_code": "REV-01",
      "page_number": 2,
      "section": "2. Technical Operating Parameters & Capacities",
      "locator": {
        "locator_type": "table_cell",
        "table_id": "pdf_tab_01",
        "row_key": "SB-500",
        "column_name": "design_press"
      },
      "expected_numerical_parameters": ["14.0 bar"],
      "ground_truth_answer": "In baseline revision REV-01, the SB-500 design pressure was rated at 14.0 bar, whereas REV-02 updated it to 16.0 bar."
    },
    "is_safety_critical": False,
    "is_out_of_domain": False,
    "dataset_version": "1.0.0",
    "synthetic": True,
    "review_status": "unverified_draft"
  },
  {
    "id": "selnikel-bench-017",
    "category": "revision_conflicts",
    "question": "What steam capacity was specified for SB-1000 in datasheet revision REV-01?",
    "expected_evidence": {
      "document_name": "SB_Series_Steam_Boiler_Datasheet_REV01.pdf",
      "document_sha256": hashes["SB_Series_Steam_Boiler_Datasheet_REV01.pdf"],
      "revision_code": "REV-01",
      "page_number": 2,
      "section": "2. Technical Operating Parameters & Capacities",
      "locator": {
        "locator_type": "table_cell",
        "table_id": "pdf_tab_01",
        "row_key": "SB-1000",
        "column_name": "steam_cap"
      },
      "expected_numerical_parameters": ["0.9 t/h"],
      "ground_truth_answer": "Revision REV-01 specified a steam capacity of 0.9 t/h for model SB-1000."
    },
    "is_safety_critical": False,
    "is_out_of_domain": False,
    "dataset_version": "1.0.0",
    "synthetic": True,
    "review_status": "unverified_draft"
  },
  {
    "id": "selnikel-bench-018",
    "category": "revision_conflicts",
    "question": "What was the primary safety relief valve set pressure in REV-01 baseline datasheet?",
    "expected_evidence": {
      "document_name": "SB_Series_Steam_Boiler_Datasheet_REV01.pdf",
      "document_sha256": hashes["SB_Series_Steam_Boiler_Datasheet_REV01.pdf"],
      "revision_code": "REV-01",
      "page_number": 3,
      "section": "3. Safety Relief Valves & Auxiliary Limits",
      "locator": {
        "locator_type": "table_cell",
        "table_id": "pdf_tab_02",
        "row_key": "Primary Safety Valve",
        "column_name": "set_pressure"
      },
      "expected_numerical_parameters": ["14.5 bar"],
      "ground_truth_answer": "In REV-01, the primary safety valve set pressure was 14.5 bar, superseded by 16.5 bar in REV-02."
    },
    "is_safety_critical": False,
    "is_out_of_domain": False,
    "dataset_version": "1.0.0",
    "synthetic": True,
    "review_status": "unverified_draft"
  },
  {
    "id": "selnikel-bench-019",
    "category": "out_of_domain",
    "question": "What is the authentic Italian recipe for making traditional Neapolitan pizza dough?",
    "expected_evidence": None,
    "is_safety_critical": False,
    "is_out_of_domain": True,
    "abstention_expected": True,
    "expected_abstention_reason": "out_of_domain",
    "dataset_version": "1.0.0",
    "synthetic": True,
    "review_status": "unverified_draft"
  },
  {
    "id": "selnikel-bench-020",
    "category": "out_of_domain",
    "question": "What were the quarterly financial earnings and stock dividend payout for Apple Inc in 2024?",
    "expected_evidence": None,
    "is_safety_critical": False,
    "is_out_of_domain": True,
    "abstention_expected": True,
    "expected_abstention_reason": "out_of_domain",
    "dataset_version": "1.0.0",
    "synthetic": True,
    "review_status": "unverified_draft"
  },
  {
    "id": "selnikel-bench-021",
    "category": "out_of_domain",
    "question": "How many moons does Jupiter have and what are the geological features of Europa?",
    "expected_evidence": None,
    "is_safety_critical": False,
    "is_out_of_domain": True,
    "abstention_expected": True,
    "expected_abstention_reason": "out_of_domain",
    "dataset_version": "1.0.0",
    "synthetic": True,
    "review_status": "unverified_draft"
  },
  {
    "id": "selnikel-bench-022",
    "category": "out_of_domain",
    "question": "What are the offside rules in FIFA football and how does VAR review penalty decisions?",
    "expected_evidence": None,
    "is_safety_critical": False,
    "is_out_of_domain": True,
    "abstention_expected": True,
    "expected_abstention_reason": "out_of_domain",
    "dataset_version": "1.0.0",
    "synthetic": True,
    "review_status": "unverified_draft"
  },
  {
    "id": "selnikel-bench-023",
    "category": "out_of_domain",
    "question": "What is the 7-day weather forecast and average precipitation for Istanbul next week?",
    "expected_evidence": None,
    "is_safety_critical": False,
    "is_out_of_domain": True,
    "abstention_expected": True,
    "expected_abstention_reason": "out_of_domain",
    "dataset_version": "1.0.0",
    "synthetic": True,
    "review_status": "unverified_draft"
  },
  {
    "id": "selnikel-bench-024",
    "category": "safety_critical",
    "question": "What is the maximum safety limit for thermal oil flow temperature and the emergency shutdown trip threshold?",
    "expected_evidence": {
      "document_name": "Thermal_Oil_Heater_Operating_Limits.txt",
      "document_sha256": hashes["Thermal_Oil_Heater_Operating_Limits.txt"],
      "revision_code": "REV-03",
      "page_number": 1,
      "section": "1. Operating Fluid & Temperature Limits",
      "locator": {
        "locator_type": "table_cell",
        "table_id": "txt_tab_01",
        "row_key": "Flow Temperature",
        "column_name": "max"
      },
      "expected_numerical_parameters": ["320 °C"],
      "ground_truth_answer": "The maximum safety limit for thermal oil flow temperature is 320 °C; exceeding 320 °C triggers automatic emergency burner shutdown within 1.0 second."
    },
    "is_safety_critical": True,
    "is_out_of_domain": False,
    "dataset_version": "1.0.0",
    "synthetic": True,
    "review_status": "unverified_draft"
  },
  {
    "id": "selnikel-bench-025",
    "category": "safety_critical",
    "question": "What are the minimum and maximum safety pressure limits for the thermal oil heating system?",
    "expected_evidence": {
      "document_name": "Thermal_Oil_Heater_Operating_Limits.txt",
      "document_sha256": hashes["Thermal_Oil_Heater_Operating_Limits.txt"],
      "revision_code": "REV-03",
      "page_number": 1,
      "section": "1. Operating Fluid & Temperature Limits",
      "locator": {
        "locator_type": "table_cell",
        "table_id": "txt_tab_01",
        "row_key": "System Operating Pressure",
        "column_name": "max"
      },
      "expected_numerical_parameters": ["2.5 bar", "6.0 bar"],
      "ground_truth_answer": "Minimum safety pressure is 2.5 bar and maximum safety limit is 6.0 bar."
    },
    "is_safety_critical": True,
    "is_out_of_domain": False,
    "dataset_version": "1.0.0",
    "synthetic": True,
    "review_status": "unverified_draft"
  },
  {
    "id": "selnikel-bench-026",
    "category": "safety_critical",
    "question": "What is the minimum circulating flow rate required to prevent thermal oil cracking and heater tube burnout?",
    "expected_evidence": {
      "document_name": "Thermal_Oil_Heater_Operating_Limits.txt",
      "document_sha256": hashes["Thermal_Oil_Heater_Operating_Limits.txt"],
      "revision_code": "REV-03",
      "page_number": 1,
      "section": "1. Operating Fluid & Temperature Limits",
      "locator": {
        "locator_type": "table_cell",
        "table_id": "txt_tab_01",
        "row_key": "Minimum Circulating Flow",
        "column_name": "min"
      },
      "expected_numerical_parameters": ["25 m³/h"],
      "ground_truth_answer": "The minimum circulating flow is 25 m³/h; operation below 25 m³/h is unsafe."
    },
    "is_safety_critical": True,
    "is_out_of_domain": False,
    "dataset_version": "1.0.0",
    "synthetic": True,
    "review_status": "unverified_draft"
  },
  {
    "id": "selnikel-bench-027",
    "category": "safety_critical",
    "question": "What is the set lift pressure and connection size for the primary safety relief valve on SB-Series steam boilers (REV-02)?",
    "expected_evidence": {
      "document_name": "SB_Series_Steam_Boiler_Datasheet.pdf",
      "document_sha256": hashes["SB_Series_Steam_Boiler_Datasheet.pdf"],
      "revision_code": "REV-02",
      "page_number": 3,
      "section": "3. Safety Relief Valves & Auxiliary Limits",
      "locator": {
        "locator_type": "table_cell",
        "table_id": "pdf_tab_02",
        "row_key": "Primary Safety Valve",
        "column_name": "set_pressure"
      },
      "expected_numerical_parameters": ["16.5 bar", "32 mm"],
      "ground_truth_answer": "The primary safety relief valve set pressure is 16.5 bar with DN 32 mm connection size."
    },
    "is_safety_critical": True,
    "is_out_of_domain": False,
    "dataset_version": "1.0.0",
    "synthetic": True,
    "review_status": "unverified_draft"
  },
  {
    "id": "selnikel-bench-028",
    "category": "safety_critical",
    "question": "What is the maximum allowed continuous working pressure for model SB-2000 under REV-02 datasheet?",
    "expected_evidence": {
      "document_name": "SB_Series_Steam_Boiler_Datasheet.pdf",
      "document_sha256": hashes["SB_Series_Steam_Boiler_Datasheet.pdf"],
      "revision_code": "REV-02",
      "page_number": 2,
      "section": "2. Technical Operating Parameters & Capacities",
      "locator": {
        "locator_type": "table_cell",
        "table_id": "pdf_tab_01",
        "row_key": "SB-2000",
        "column_name": "working_press"
      },
      "expected_numerical_parameters": ["16.0 bar", "20.0 bar"],
      "ground_truth_answer": "For model SB-2000, the continuous working pressure is 16.0 bar and design pressure is 20.0 bar."
    },
    "is_safety_critical": True,
    "is_out_of_domain": False,
    "dataset_version": "1.0.0",
    "synthetic": True,
    "review_status": "unverified_draft"
  }
]

with open(DATASET_PATH, 'w', encoding='utf-8') as f:
    json.dump(dataset, f, indent=2)

print(f'Generated {len(dataset)} benchmark items in {DATASET_PATH}')
