"""
Benchmark Dataset Validator & Schema Integrity Checker.
Ensures benchmark records meet governance rules: SHA-256 presence, valid pages, parseable parameters, locator coordinates, and conditional review status.
"""
import hashlib
import json
import jsonschema
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from app.domain.contracts.evaluation import BenchmarkQuestion, AbstentionReason, LocatorType
from app.services.evaluation.metrics import extract_parameters


def validate_dataset_file(
    dataset_path: Path,
    schema_path: Optional[Path] = None,
    verify_files_dir: Optional[Path] = None,
) -> Tuple[bool, List[str]]:
    """
    Validates a benchmark JSON dataset against schema, domain invariants, and physical fixture coordinates.
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

    # 2. Domain-level & Invariant Validation
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

                    # Physical file & coordinate verification
                    if verify_files_dir and verify_files_dir.exists():
                        doc_path = verify_files_dir / ev.document_name
                        if not doc_path.exists():
                            errors.append(f"Question '{q.id}' references missing fixture file: {doc_path}")
                        elif ev.document_sha256:
                            with open(doc_path, "rb") as df:
                                actual_sha = hashlib.sha256(df.read()).hexdigest()
                            if actual_sha.lower() != ev.document_sha256.lower():
                                errors.append(
                                    f"Question '{q.id}' SHA-256 mismatch for {ev.document_name}: expected {ev.document_sha256}, got {actual_sha}"
                                )

        except Exception as pe:
            errors.append(f"Validation error at item index {idx}: {pe}")

    return len(errors) == 0, errors