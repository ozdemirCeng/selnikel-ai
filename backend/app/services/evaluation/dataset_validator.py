"""
Benchmark Dataset Validator & Schema Integrity Checker.
Ensures benchmark records meet governance rules: SHA-256 presence, valid pages, non-empty parameters, expert review.
"""
import json
import jsonschema
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from app.domain.contracts.evaluation import BenchmarkQuestion


def validate_dataset_file(dataset_path: Path, schema_path: Optional[Path] = None) -> Tuple[bool, List[str]]:
    """
    Validates a benchmark JSON dataset against schema and domain invariants.
    Returns (is_valid, error_messages).
    """
    errors: List[str] = []
    if not dataset_path.exists():
        return False, [f"Dataset file does not exist: {dataset_path}"]

    try:
        with open(dataset_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except Exception as e:
        return False, [f"JSON parsing error in dataset: {e}"]

    if not isinstance(raw_data, list):
        return False, ["Dataset root element must be a JSON array of questions."]

    # Optional JSON schema validation
    if schema_path and schema_path.exists():
        try:
            with open(schema_path, "r", encoding="utf-8") as sf:
                schema = json.load(sf)
            jsonschema.validate(instance=raw_data, schema=schema)
        except jsonschema.ValidationError as ve:
            errors.append(f"JSON Schema Validation Error: {ve.message} at path {list(ve.path)}")
        except Exception as se:
            errors.append(f"Schema validation error: {se}")

    # Domain-level validation
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

            if not q.is_out_of_domain:
                if not q.expected_evidence.document_name.strip():
                    errors.append(f"In-domain question '{q.id}' missing expected document_name.")
                if q.expected_evidence.page_number <= 0:
                    errors.append(f"In-domain question '{q.id}' has invalid page_number {q.expected_evidence.page_number}.")
                if not q.expected_evidence.ground_truth_answer.strip():
                    errors.append(f"In-domain question '{q.id}' missing ground_truth_answer.")

        except Exception as pe:
            errors.append(f"Validation error at item index {idx}: {pe}")

    return len(errors) == 0, errors
