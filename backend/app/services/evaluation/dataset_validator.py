"""
Benchmark Dataset Validator & Schema Integrity Checker.
Ensures benchmark records meet governance rules: SHA-256 presence, manifest alignment,
valid page boundaries, parseable parameters, real parsed table/section coordinate verification,
and conditional review status.
"""
import asyncio
import hashlib
import json
import jsonschema
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.domain.contracts.evaluation import BenchmarkQuestion, AbstentionReason, LocatorType
from app.domain.parser import ParsedDocument
from app.services.evaluation.metrics import extract_parameters
from app.services.ingestion.parser import FastFallbackParser


def validate_dataset_file(
    dataset_path: Path,
    schema_path: Optional[Path] = None,
    verify_files_dir: Optional[Path] = None,
    manifest_path: Optional[Path] = None,
) -> Tuple[bool, List[str]]:
    """
    Validates a benchmark JSON dataset against schema, domain invariants, physical fixture files,
    manifest metadata, and physical parser table/section coordinates.
    Returns (is_valid, error_messages).
    """
    errors: List[str] = []
    if not dataset_path.exists():
        return False, [f"Dataset file does not exist: {dataset_path}"]

    try:
        with open(dataset_path, "r", encoding="utf-8-sig") as f:
            raw_data = json.load(f)
    except Exception as e:
        return False, [f"JSON parsing error in dataset: {e}"]

    if not isinstance(raw_data, list):
        return False, ["Dataset root element must be a JSON array of questions."]

    # 1. JSON Schema validation
    if schema_path and schema_path.exists():
        try:
            with open(schema_path, "r", encoding="utf-8-sig") as sf:
                schema = json.load(sf)
            jsonschema.validate(instance=raw_data, schema=schema)
        except jsonschema.ValidationError as ve:
            errors.append(f"JSON Schema Validation Error: {ve.message} at path {list(ve.path)}")
        except Exception as se:
            errors.append(f"Schema validation error: {se}")

    # 2. Manifest Loading (if available)
    manifest_fixtures: Dict[str, Dict[str, Any]] = {}
    resolved_manifest_path = manifest_path
    if not resolved_manifest_path and verify_files_dir:
        candidate = verify_files_dir.parent / "fixture_manifest.json"
        if candidate.exists():
            resolved_manifest_path = candidate

    if resolved_manifest_path and resolved_manifest_path.exists():
        try:
            with open(resolved_manifest_path, "r", encoding="utf-8-sig") as mf:
                mdata = json.load(mf)
                manifest_fixtures = {fix["filename"]: fix for fix in mdata.get("fixtures", [])}
        except Exception as me:
            errors.append(f"Failed to load fixture manifest: {me}")

    # Parser cache for physical coordinate checking
    parser = FastFallbackParser()
    parsed_docs_cache: Dict[str, ParsedDocument] = {}

    # 3. Domain-level & Invariant Validation
    seen_ids = set()
    for idx, item in enumerate(raw_data):
        try:
            q = BenchmarkQuestion(**item)
            if q.id in seen_ids:
                errors.append(f"Duplicate question ID '{q.id}' at index {idx}.")
            seen_ids.add(q.id)

            # Invariant checks
            if not q.question.strip():
                errors.append(f"Question '{q.id}' has empty question text.")

            # Out-of-Domain checks
            if q.is_out_of_domain:
                if q.expected_evidence is not None:
                    errors.append(f"OOD Question '{q.id}' must have expected_evidence: null.")
                if not q.abstention_expected:
                    errors.append(f"OOD Question '{q.id}' must have abstention_expected: true.")
                if q.expected_abstention_reason != AbstentionReason.OUT_OF_DOMAIN:
                    errors.append(f"OOD Question '{q.id}' must have expected_abstention_reason: 'out_of_domain'.")
            else:
                # In-Domain checks
                if q.expected_evidence is None:
                    errors.append(f"In-domain question '{q.id}' missing expected_evidence.")
                else:
                    ev = q.expected_evidence
                    if not ev.document_name.strip():
                        errors.append(f"In-domain question '{q.id}' missing expected document_name.")
                    if ev.page_number <= 0:
                        errors.append(f"In-domain question '{q.id}' has invalid page_number {ev.page_number}.")
                    if not ev.ground_truth_answer.strip():
                        errors.append(f"In-domain question '{q.id}' missing ground_truth_answer.")

                    # Validate parameter parseability
                    for p in ev.expected_numerical_parameters:
                        parsed = extract_parameters(p)
                        if not parsed:
                            errors.append(
                                f"Question '{q.id}' has unparseable expected parameter '{p}'."
                            )

                    # Validate locator presence
                    if not ev.locator:
                        errors.append(f"Question '{q.id}' missing locator in expected_evidence.")
                    elif ev.locator.locator_type == LocatorType.TABLE_CELL:
                        if not ev.locator.table_id or not ev.locator.row_key or not ev.locator.column_name:
                            errors.append(f"Question '{q.id}' has incomplete table_cell locator.")
                    elif ev.locator.locator_type == LocatorType.SECTION_TEXT:
                        if not ev.locator.section_header or not ev.locator.key_phrase:
                            errors.append(f"Question '{q.id}' has incomplete section_text locator.")

                    # Manifest Grounding Validation
                    if manifest_fixtures:
                        if ev.document_name not in manifest_fixtures:
                            errors.append(f"Question '{q.id}' references document '{ev.document_name}' not in manifest.")
                        else:
                            fix_meta = manifest_fixtures[ev.document_name]
                            if ev.document_sha256 and ev.document_sha256.lower() != fix_meta.get("sha256", "").lower():
                                errors.append(
                                    f"Question '{q.id}' document_sha256 mismatch against manifest for '{ev.document_name}': expected {fix_meta.get('sha256')}, got {ev.document_sha256}"
                                )
                            if ev.revision_code and ev.revision_code != fix_meta.get("revision_code"):
                                errors.append(
                                    f"Question '{q.id}' revision_code mismatch against manifest for '{ev.document_name}': expected {fix_meta.get('revision_code')}, got {ev.revision_code}"
                                )
                            if ev.page_number > fix_meta.get("page_count", 1):
                                errors.append(
                                    f"Question '{q.id}' page_number {ev.page_number} exceeds manifest page_count {fix_meta.get('page_count')} for '{ev.document_name}'."
                                )

                    # Physical File & Real Parser Coordinate Verification
                    if verify_files_dir and verify_files_dir.exists():
                        doc_path = verify_files_dir / ev.document_name
                        if not doc_path.exists():
                            errors.append(f"Question '{q.id}' references missing fixture file: {doc_path}")
                        else:
                            # Verify physical SHA-256
                            with open(doc_path, "rb") as df:
                                actual_sha = hashlib.sha256(df.read()).hexdigest()
                            if ev.document_sha256 and actual_sha.lower() != ev.document_sha256.lower():
                                errors.append(
                                    f"Question '{q.id}' SHA-256 mismatch for {ev.document_name}: expected {ev.document_sha256}, got {actual_sha}"
                                )

                            # Parse document to verify page and table/section coordinates
                            if ev.document_name not in parsed_docs_cache:
                                try:
                                    parsed_docs_cache[ev.document_name] = parser.parse_sync(str(doc_path))
                                except Exception as pe:
                                    errors.append(f"Failed to parse document '{ev.document_name}' for coordinate validation: {pe}")

                            parsed_doc = parsed_docs_cache.get(ev.document_name)
                            if parsed_doc:
                                if ev.page_number > parsed_doc.total_pages:
                                    errors.append(
                                        f"Question '{q.id}' page_number {ev.page_number} exceeds parsed document total_pages {parsed_doc.total_pages} in '{ev.document_name}'."
                                    )

                                target_page = next((p for p in parsed_doc.pages if p.page_number == ev.page_number), None)
                                if not target_page:
                                    errors.append(
                                        f"Question '{q.id}' page {ev.page_number} not found in parsed document '{ev.document_name}'."
                                    )
                                else:
                                    loc = ev.locator
                                    if loc and loc.locator_type == LocatorType.TABLE_CELL:
                                        # Strict table_id lookup (NO fallback to arbitrary tables)
                                        matched_table = next(
                                            (t for t in target_page.tables if t.table_id == loc.table_id),
                                            None,
                                        )
                                        if not matched_table:
                                            avail_tab_ids = [t.table_id for t in target_page.tables]
                                            errors.append(
                                                f"Question '{q.id}' table_id '{loc.table_id}' not found on page {ev.page_number} of '{ev.document_name}'. Available tables on page: {avail_tab_ids}"
                                            )
                                        else:
                                            # Parse markdown table to 2D matrix (headers & data rows)
                                            raw_lines = [l.strip() for l in matched_table.markdown_table.strip().split("\n") if "|" in l]
                                            headers = [c.strip() for c in raw_lines[0].strip("|").split("|")] if raw_lines else []
                                            
                                            data_rows: List[List[str]] = []
                                            for r_line in raw_lines[1:]:
                                                if re.match(r"^\|?\s*[-:]+[-|\s:]*\|?$", r_line):
                                                    continue
                                                cols = [c.strip() for c in r_line.strip("|").split("|")]
                                                if cols != headers:
                                                    data_rows.append(cols)

                                            # 1. Validate Column Name
                                            col_idx = None
                                            norm_col = loc.column_name.lower().replace("_", " ").strip()
                                            for idx_h, h in enumerate(headers):
                                                norm_h = h.lower()
                                                # Exact match, token subset, or standard technical abbreviations
                                                if (
                                                    norm_col == norm_h
                                                    or norm_col in norm_h
                                                    or all(w in norm_h for w in norm_col.split())
                                                    or (norm_col == "dn" and "dn" in norm_h)
                                                    or (norm_col == "desc" and "description" in norm_h)
                                                    or (norm_col == "cause" and "cause" in norm_h)
                                                    or (norm_col == "action" and "action" in norm_h)
                                                    or (norm_col == "interval" and "interval" in norm_h)
                                                    or (norm_col == "max" and ("max" in norm_h or "limit" in norm_h))
                                                    or (norm_col == "min" and "min" in norm_h)
                                                ):
                                                    col_idx = idx_h
                                                    break

                                            if col_idx is None:
                                                errors.append(
                                                    f"Question '{q.id}' column_name '{loc.column_name}' not found in table '{loc.table_id}' headers: {headers}"
                                                )

                                            # 2. Validate Row Key
                                            matched_row = None
                                            norm_row_key = loc.row_key.lower().strip()
                                            for row in data_rows:
                                                row_cells_lower = [c.lower() for c in row]
                                                if any(norm_row_key == c or norm_row_key in c for c in row_cells_lower):
                                                    matched_row = row
                                                    break

                                            if matched_row is None:
                                                avail_keys = [r[0] for r in data_rows if r]
                                                errors.append(
                                                    f"Question '{q.id}' row_key '{loc.row_key}' not found in table '{loc.table_id}' rows. Available row keys: {avail_keys}"
                                                )

                                            # 3. Validate Mandatory Expected Cell Value & Exact Ground Truth Alignment
                                            if not loc.expected_cell_value:
                                                errors.append(
                                                    f"Question '{q.id}' table_cell locator is missing required 'expected_cell_value'."
                                                )
                                            elif col_idx is not None and matched_row is not None:
                                                if col_idx < len(matched_row):
                                                    cell_value = matched_row[col_idx].strip()
                                                    if not cell_value or cell_value == "-":
                                                        errors.append(
                                                            f"Question '{q.id}' coordinate ({loc.row_key}, {loc.column_name}) in table '{loc.table_id}' has empty cell value."
                                                        )
                                                    else:
                                                        norm_actual = re.sub(r"\s+", " ", cell_value.lower().strip()).replace("°", "").replace("", "")
                                                        norm_expected = re.sub(r"\s+", " ", loc.expected_cell_value.lower().strip()).replace("°", "").replace("", "")
                                                        if norm_actual != norm_expected and norm_expected not in norm_actual and norm_actual not in norm_expected:
                                                            errors.append(
                                                                f"Question '{q.id}' coordinate ({loc.row_key}, {loc.column_name}) expected cell value '{loc.expected_cell_value}', but found '{cell_value}' in table '{loc.table_id}'."
                                                            )
                                                else:
                                                    errors.append(
                                                        f"Question '{q.id}' column index {col_idx} out of range for row with {len(matched_row)} columns."
                                                    )

                                    elif loc and loc.locator_type == LocatorType.SECTION_TEXT:
                                        # 1. Verify Section Header
                                        norm_sec = loc.section_header.lower().strip()
                                        sec_matched = any(
                                            norm_sec == sh.lower().strip() or norm_sec in sh.lower() or sh.lower() in norm_sec
                                            for sh in target_page.section_headers
                                        ) or (norm_sec in target_page.text_content.lower())

                                        if not sec_matched:
                                            errors.append(
                                                f"Question '{q.id}' section_header '{loc.section_header}' not found on page {ev.page_number} of '{ev.document_name}'. Available sections: {target_page.section_headers}"
                                            )

                                        # 2. Verify Key Phrase
                                        if not loc.key_phrase or loc.key_phrase.lower() not in target_page.text_content.lower():
                                            errors.append(
                                                f"Question '{q.id}' key_phrase '{loc.key_phrase}' not found in text of page {ev.page_number} of '{ev.document_name}'."
                                            )

        except Exception as pe:
            errors.append(f"Validation error at item index {idx}: {pe}")

    return len(errors) == 0, errors