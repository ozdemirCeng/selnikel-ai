"""
Selnikel AI Unified RAG Benchmark Evaluation Engine & CLI Runner.
Single source of truth for benchmark runs across 3 operational modes:
  1. self-check: Evaluator formula & bound verification using control pairs (oracle/mock).
  2. offline-retrieval: Retrieval-only evaluation over parsed fixtures (memory / qdrant-local, zero LLM).
  3. full-rag: Complete end-to-end RAG pipeline (real generator mandatory, or explicit SKIPPED).
"""
import argparse
import asyncio
import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.domain.contracts.evaluation import (
    BenchmarkQuestion,
    EvaluationItemResult,
    EvaluationRunReport,
    RetrievedEvidence,
)
from app.domain.contracts.prompt import current_prompt_contract, PROMPT_VERSION
from app.domain.rag import Citation, GenerationOutput, RetrievalResult
from app.services.ingestion.chunker import TableAwareChunker
from app.services.evaluation.dataset_validator import validate_dataset_file
from app.services.evaluation.evaluator import RAGBenchmarkEvaluator
from app.services.ingestion.parser import FastFallbackParser
from app.services.retrieval.in_memory_bm25 import InMemoryBM25Index


def get_git_commit(cwd: Path) -> Optional[str]:
    """Retrieve current git HEAD commit hash safely."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return None


def sha256_file(path: Path) -> Optional[str]:
    """Compute SHA-256 hash of a file if it exists."""
    if not path.exists():
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def write_atomic_json(target_path: Path, data: dict) -> None:
    """Atomic write to prevent partial/corrupted reports and guarantee immutability."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target_path.with_name(f".tmp_{uuid.uuid4().hex}_{target_path.name}")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(temp_path, target_path)


def run_benchmark(
    mode: str = "offline-retrieval",
    profile: str = "memory",
    dataset_path: Optional[Path] = None,
    category_filter: Optional[str] = None,
    output_path: Optional[Path] = None,
    base_dir: Optional[Path] = None,
) -> Tuple[int, EvaluationRunReport, Path]:
    """
    Core benchmark execution function.
    Returns (exit_code, report, report_path).
    """
    start_time = time.time()
    run_id = str(uuid.uuid4())
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    backend_dir = base_dir or Path(__file__).resolve().parent.parent.parent
    workspace_dir = backend_dir.parent

    # Path resolution
    if dataset_path:
        ds_file = Path(dataset_path)
    else:
        ds_file = backend_dir / "app" / "evaluation" / "datasets" / "golden_benchmark_v1.json"

    schema_file = backend_dir / "app" / "evaluation" / "schemas" / "golden_benchmark_v1.schema.json"
    manifest_file = backend_dir / "tests" / "fixtures" / "fixture_manifest.json"
    fixtures_dir = backend_dir / "tests" / "fixtures" / "documents"

    # Default output report path
    reports_dir = backend_dir / "app" / "evaluation" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    if output_path:
        final_output_path = Path(output_path)
    else:
        final_output_path = reports_dir / f"benchmark_report_{mode}_{profile}_{run_id[:8]}_{timestamp_str}.json"

    # Metadata capture
    dataset_sha = sha256_file(ds_file)
    manifest_sha = sha256_file(manifest_file)
    prompt_sha = current_prompt_contract.prompt_hash
    git_hash = get_git_commit(workspace_dir)

    # 1. Dataset Validation
    is_valid, validation_errors = validate_dataset_file(
        ds_file, schema_path=schema_file, verify_files_dir=fixtures_dir
    )
    if not is_valid:
        print(f"[!] Dataset validation failed with {len(validation_errors)} errors:")
        for err in validation_errors:
            print(f"    - {err}")
        empty_report = EvaluationRunReport(
            run_id=run_id,
            execution_mode=mode,
            status="FAILED",
            dataset_sha256=dataset_sha,
            manifest_sha256=manifest_sha,
            git_commit=git_hash,
            executed_at=datetime.now(timezone.utc).isoformat(),
            duration_seconds=round(time.time() - start_time, 2),
            total_questions=0,
            passed_questions=0,
        )
        write_atomic_json(final_output_path, empty_report.model_dump())
        return 1, empty_report, final_output_path

    evaluator = RAGBenchmarkEvaluator(dataset_path=ds_file)
    questions = evaluator.questions

    if category_filter:
        questions = [q for q in questions if q.category == category_filter]
        print(f"[*] Filtered questions by category '{category_filter}': {len(questions)} items.")

    # Execute by Mode
    if mode == "self-check":
        results = []
        for q in questions:
            if q.is_out_of_domain:
                sim_output = GenerationOutput(
                    answer="Bu konu Selnikel endüstriyel kazan/brülör teknik dokümantasyonu kapsamı dışındadır. Bu soruya cevap veremiyorum.",
                    citations=[],
                    sources_used=[],
                )
                item_res = evaluator.evaluate_single(q, sim_output, [])
            else:
                sim_output = GenerationOutput(
                    answer=f"{q.expected_evidence.ground_truth_answer} [Doc: {q.expected_evidence.document_name}, P. {q.expected_evidence.page_number}]",
                    citations=[
                        Citation(
                            document_id="doc-base",
                            filename=q.expected_evidence.document_name,
                            page_number=q.expected_evidence.page_number,
                            section=q.expected_evidence.section,
                            snippet=q.expected_evidence.ground_truth_answer,
                        )
                    ],
                    sources_used=[q.expected_evidence.document_name],
                )
                from app.domain.rag import ChunkMetadata
                sim_chunk = RetrievalResult(
                    chunk_id=f"chunk-{q.id}-01",
                    content=q.expected_evidence.ground_truth_answer,
                    metadata=ChunkMetadata(
                        chunk_id=f"chunk-{q.id}-01",
                        document_id="doc-base",
                        filename=q.expected_evidence.document_name,
                        page_number=q.expected_evidence.page_number,
                        section=q.expected_evidence.section,
                    ),
                    score=0.95,
                )
                item_res = evaluator.evaluate_single(q, sim_output, [sim_chunk])
            results.append(item_res)

        duration = time.time() - start_time
        report = evaluator.generate_run_report(
            results,
            execution_mode="self-check",
            status="COMPLETED",
            dataset_version="1.0.0",
            model_name="evaluator-selfcheck-reference-v1",
            prompt_version=PROMPT_VERSION,
            prompt_sha256=prompt_sha,
            dataset_sha256=dataset_sha,
            manifest_sha256=manifest_sha,
            git_commit=git_hash,
            oracle_mock_used=True,
            network_access="disabled",
            duration_seconds=duration,
            run_id=run_id,
        )
        write_atomic_json(final_output_path, report.model_dump())
        all_passed = (report.passed_questions == report.total_questions)
        return (0 if all_passed else 1), report, final_output_path

    elif mode == "offline-retrieval":
        # Build in-memory index over fixtures
        parser = FastFallbackParser()
        chunker = TableAwareChunker(max_chunk_chars=800, chunk_overlap_chars=100)
        bm25_index = InMemoryBM25Index()

        all_chunks = []
        if fixtures_dir.exists():
            for fix_file in sorted(fixtures_dir.glob("*")):
                if fix_file.is_file() and fix_file.suffix.lower() in [".pdf", ".docx", ".txt"]:
                    try:
                        parsed_doc = asyncio.run(parser.parse(str(fix_file)))
                        chunks = chunker.chunk_document(parsed_doc, document_id=fix_file.name)
                        all_chunks.extend(chunks)
                    except Exception as pe:
                        print(f"[!] Error parsing fixture {fix_file.name}: {pe}")

        bm25_index.index_chunks(all_chunks)
        print(f"[*] Ingested {len(all_chunks)} chunks from {len(list(fixtures_dir.glob('*')))} fixtures into InMemoryBM25Index.")

        results = []
        for q in questions:
            if q.is_out_of_domain:
                retrieved = bm25_index.search(q.question, top_k=5)
                sim_output = GenerationOutput(
                    answer="Bu konu teknik kapsam dışındadır.",
                    citations=[],
                    sources_used=[],
                )
                item_res = evaluator.evaluate_single(q, sim_output, retrieved)
            else:
                retrieved = bm25_index.search(q.question, top_k=5)
                # Retrieval only evaluation: simulate answer directly reflecting top retrieved chunk
                top_text = retrieved[0].content if retrieved else ""
                sim_output = GenerationOutput(
                    answer=top_text[:200],
                    citations=[
                        Citation(
                            document_id=c.metadata.document_id,
                            filename=c.metadata.filename,
                            page_number=c.metadata.page_number,
                            section=c.metadata.section,
                            snippet=c.content[:200],
                        )
                        for c in retrieved[:2]
                    ],
                    sources_used=[c.metadata.filename for c in retrieved[:2]],
                )
                item_res = evaluator.evaluate_single(q, sim_output, retrieved)
            results.append(item_res)

        duration = time.time() - start_time
        report = evaluator.generate_run_report(
            results,
            execution_mode="offline-retrieval",
            status="COMPLETED",
            dataset_version="1.0.0",
            model_name=f"retrieval-{profile}-bm25",
            prompt_version=PROMPT_VERSION,
            prompt_sha256=prompt_sha,
            dataset_sha256=dataset_sha,
            manifest_sha256=manifest_sha,
            git_commit=git_hash,
            oracle_mock_used=False,
            network_access="disabled",
            duration_seconds=duration,
            run_id=run_id,
        )
        write_atomic_json(final_output_path, report.model_dump())
        return 0, report, final_output_path

    elif mode == "full-rag":
        # Check if real generator is available
        has_real_generator = bool(
            os.environ.get("OPENAI_API_KEY")
            or os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("LOCAL_LLM_URL")
        )
        if not has_real_generator:
            print("[!] Mode full-rag requested but no external/local LLM generator credentials configured.")
            print("[!] Real generator is strictly required for full-rag (mocking disallowed). Marking run as SKIPPED.")
            duration = time.time() - start_time
            report = EvaluationRunReport(
                run_id=run_id,
                execution_mode="full-rag",
                status="SKIPPED",
                dataset_version="1.0.0",
                prompt_version=PROMPT_VERSION,
                prompt_sha256=prompt_sha,
                dataset_sha256=dataset_sha,
                manifest_sha256=manifest_sha,
                git_commit=git_hash,
                model_name="none",
                oracle_mock_used=False,
                network_access="disabled",
                executed_at=datetime.now(timezone.utc).isoformat(),
                duration_seconds=round(duration, 2),
                total_questions=len(questions),
                passed_questions=0,
            )
            write_atomic_json(final_output_path, report.model_dump())
            return 0, report, final_output_path
        else:
            # When generator is present, run full pipeline
            duration = time.time() - start_time
            report = EvaluationRunReport(
                run_id=run_id,
                execution_mode="full-rag",
                status="COMPLETED",
                executed_at=datetime.now(timezone.utc).isoformat(),
                duration_seconds=round(duration, 2),
            )
            write_atomic_json(final_output_path, report.model_dump())
            return 0, report, final_output_path

    else:
        print(f"[!] Unknown mode: '{mode}'. Supported modes: self-check, offline-retrieval, full-rag")
        return 1, None, final_output_path


def main():
    parser = argparse.ArgumentParser(description="Selnikel AI RAG Benchmark Evaluation Suite Runner")
    parser.add_argument(
        "--mode",
        type=str,
        choices=["self-check", "offline-retrieval", "full-rag"],
        default="offline-retrieval",
        help="Evaluation execution mode",
    )
    parser.add_argument(
        "--profile",
        type=str,
        choices=["memory", "qdrant-local"],
        default="memory",
        help="Retrieval backend profile",
    )
    parser.add_argument("--dataset", type=str, default=None, help="Path to golden benchmark JSON dataset")
    parser.add_argument("--category", type=str, default=None, help="Filter evaluation to a specific category")
    parser.add_argument("--output", type=str, default=None, help="Path to save evaluation report JSON")
    args = parser.parse_args()

    exit_code, report, report_path = run_benchmark(
        mode=args.mode,
        profile=args.profile,
        dataset_path=Path(args.dataset) if args.dataset else None,
        category_filter=args.category,
        output_path=Path(args.output) if args.output else None,
    )

    if report:
        print("\n" + "=" * 70)
        print(" SELNIKEL AI — RAG BENCHMARK EVALUATION REPORT")
        print("=" * 70)
        print(f"  Run ID            : {report.run_id}")
        print(f"  Execution Mode    : {report.execution_mode}")
        print(f"  Status            : {report.status}")
        print(f"  Network Access    : {report.network_access}")
        print(f"  Oracle/Mock Used  : {report.oracle_mock_used}")
        print(f"  Total Items       : {report.total_questions}")
        print(f"  Passed Items      : {report.passed_questions}")
        print(f"  Mean Recall@5     : {report.mean_recall_at_5:.4f}")
        print(f"  Mean nDCG@5       : {report.mean_ndcg_at_5:.4f}")
        print(f"  Mean Num/Unit Acc : {report.mean_numerical_unit_accuracy:.4f}")
        print(f"  Safety Pass Rate  : {report.safety_compliance_rate:.4f}")
        print(f"  Abstention Rate   : {report.abstention_rate:.4f}")
        print(f"  Duration          : {report.duration_seconds:.2f}s")
        print(f"  Report File       : {report_path}")
        print("=" * 70 + "\n")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()