"""
CLI Command: Validate Benchmark Dataset Integrity & Schema Compliance.
Usage:
    python -m app.cli.validate_dataset [path/to/dataset.json]
"""
import sys
from pathlib import Path
from app.services.evaluation.dataset_validator import validate_dataset_file


def main():
    if len(sys.argv) > 1:
        dataset_path = Path(sys.argv[1])
    else:
        dataset_path = Path(__file__).resolve().parent.parent / "evaluation" / "datasets" / "golden_benchmark_baseline.json"

    schema_path = Path(__file__).resolve().parent.parent / "evaluation" / "schemas" / "golden_benchmark_v1.schema.json"

    print(f"[*] Validating benchmark dataset: {dataset_path}")
    print(f"[*] Schema path: {schema_path}")

    is_valid, errors = validate_dataset_file(dataset_path, schema_path)
    if is_valid:
        print("[+] SUCCESS: Benchmark dataset is 100% valid and adheres to all schema and governance rules.")
        sys.exit(0)
    else:
        print("[-] FAILED: Dataset validation errors found:")
        for err in errors:
            print(f"    - {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
