"""
Benchmark Dataset Validator & Schema Integrity Checker.
Ensures benchmark records meet governance rules: SHA-256 presence, valid pages, parseable parameters, and conditional review status.
"""
import hashlib
import json
import jsonschema
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from app.domain.contracts.evaluation import BenchmarkQuestion
from app.services.evaluation.metrics import extract_parameters


def validate_dataset_file(
    dataset_path: Path,
    schema_path: Optional[Path] = None,
    verify_files_dir: Optional[Path] = None,
) -> Tuple[bool, List[str]]:
    """
    Validates a benchmark JSON dataset against schema and domain invariants.
    Optionally verifies physical document files and SHA-256 hashes if verify_files_dir is provided.
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

    # 1. JSON Schema validation
    if schema_path and schema_path.exists():
        try:
            with open(schema_path, "r", encoding="utf-8") as sf:
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

            # Validate parameter parseability
            for p in q.expected_evidence.expected_numerical_parameters:
                parsed = extract_parameters(p)
                if not parsed:
                    errors.append(
                        f"Question '{q.id}' has unparseable expected parameter '{p}'."
                    )

            # Strict rules for verified_expert_reviewed items
            if q.review_status == "verified_expert_reviewed":
                if q.synthetic:
                    errors.append(f"Question '{q.id}' has review_status 'verified_expert_reviewed' but synthetic is True.")
                if not q.expert_reviewer or len(q.expert_reviewer.strip()) < 3:
                    errors.append(f"Question '{q.id}' marked verified_expert_reviewed but missing expert_reviewer.")
                if not q.expected_evidence.document_sha256 or len(q.expected_evidence.document_sha256) != 64:
                    errors.append(f"Question '{q.id}' marked verified_expert_reviewed but missing 64-char document_sha256.")
                if not q.expected_evidence.revision_code:
                    errors.append(f"Question '{q.id}' marked verified_expert_reviewed but missing revision_code.")

            if not q.is_out_of_domain:
                if not q.expected_evidence.document_name.strip():
                    errors.append(f"In-domain question '{q.id}' missing expected document_name.")
                if q.expected_evidence.page_number <= 0:
                    errors.append(f"In-domain question '{q.id}' has invalid page_number {q.expected_evidence.page_number}.")
                if not q.expected_evidence.ground_truth_answer.strip():
                    errors.append(f"In-domain question '{q.id}' missing ground_truth_answer.")

            # Optional physical file and hash check
            if verify_files_dir and verify_files_dir.exists() and not q.is_out_of_domain:
                doc_path = verify_files_dir / q.expected_evidence.document_name
                if not doc_path.exists():
                    errors.append(f"Referenced document file not found: {doc_path}")
                elif q.expected_evidence.document_sha256:
                    with open(doc_path, "rb") as df:
                        actual_sha = hashlib.sha256(df.read()).hexdigest()
                    if actual_sha.lower() != q.expected_evidence.document_sha256.lower():
                        errors.append(
                            f"SHA-256 mismatch for {q.expected_evidence.document_name}: expected {q.expected_evidence.document_sha256}, got {actual_sha}"
                        )

        except Exception as pe:
            errors.append(f"Validation error at item index {idx}: {pe}")

    return len(errors) == 0, errors
