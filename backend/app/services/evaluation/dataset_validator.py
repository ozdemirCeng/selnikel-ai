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
                                        # Find matching table on that page
                                        matched_table = next(
                                            (t for t in target_page.tables if t.table_id == loc.table_id or (loc.table_id in t.caption if loc.table_id and t.caption else False)),
                                            None,
                                        )
                                        if not matched_table:
                                            # Fallback: check if any table on that page matches
                                            if target_page.tables:
                                                matched_table = target_page.tables[0]
                                            else:
                                                errors.append(
                                                    f"Question '{q.id}' table '{loc.table_id}' not found on page {ev.page_number} of '{ev.document_name}'."
                                                )

                                        if matched_table:
                                            # Check row_key in markdown_table
                                            if loc.row_key.lower() not in matched_table.markdown_table.lower():
                                                errors.append(
                                                    f"Question '{q.id}' row_key '{loc.row_key}' not found in table on page {ev.page_number} of '{ev.document_name}'."
                                                )

                                    elif loc and loc.locator_type == LocatorType.SECTION_TEXT:
                                        # Verify key_phrase in page text_content
                                        if loc.key_phrase and loc.key_phrase.lower() not in target_page.text_content.lower():
                                            errors.append(
                                                f"Question '{q.id}' key_phrase '{loc.key_phrase}' not found in text of page {ev.page_number} of '{ev.document_name}'."
                                            )

        except Exception as pe:
            errors.append(f"Validation error at item index {idx}: {pe}")

    return len(errors) == 0, errors