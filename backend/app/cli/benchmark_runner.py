"""
Selnikel AI Unified RAG Benchmark Evaluation Engine & CLI Runner.
Single source of truth for benchmark runs across 3 operational modes:
  1. self-check: Evaluator formula & bound verification using control pairs (oracle/mock).
  2. offline-retrieval: Pure retrieval-only evaluation over parsed fixtures (memory / qdrant-local, zero LLM).
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
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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


def write_atomic_json(target_path: Path, data: dict, overwrite: bool = False) -> None:
    """
    Atomic write to prevent partial/corrupted reports and guarantee immutability.
    Refuses to overwrite existing reports unless overwrite=True.
    """
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if target_path.exists() and not overwrite:
        raise FileExistsError(f"Immutable report file already exists: {target_path}")

    temp_path = target_path.with_name(f".tmp_{uuid.uuid4().hex}_{target_path.name}")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(temp_path, target_path)


def check_qdrant_health(host: str = "localhost", port: int = 6333) -> bool:
    """Check if local Qdrant instance is reachable and ready."""
    try:
        url = f"http://{host}:{port}/readyz"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=2) as response:
            return response.status == 200
    except Exception:
        return False


def check_local_llm_health(url: str) -> bool:
    """Check if local LLM endpoint is reachable and responsive."""
    try:
        health_url = url.rstrip("/") + "/health"
        req = urllib.request.Request(health_url, method="GET")
        with urllib.request.urlopen(req, timeout=2) as response:
            return response.status in [200, 204]
    except Exception:
        # Try root endpoint
        try:
            req = urllib.request.Request(url.rstrip("/"), method="GET")
            with urllib.request.urlopen(req, timeout=2) as response:
                return response.status in [200, 204, 404]
        except Exception:
            return False


def build_retrieval_index(
    profile: str,
    fixtures_dir: Path,
) -> Tuple[Any, str, str]:
    """
    Build and return the appropriate retriever based on the profile.
    Returns (retriever_instance, model_name, network_access).
    """
    if profile == "memory":
        parser = FastFallbackParser()
        chunker = TableAwareChunker(max_chunk_chars=800, chunk_overlap_chars=100)
        bm25_index = InMemoryBM25Index()

        all_chunks = []
        if fixtures_dir.exists():
            for fix_file in sorted(fixtures_dir.glob("*")):
                if fix_file.is_file() and fix_file.suffix.lower() in [".pdf", ".docx", ".txt"]:
                    try:
                        parsed_doc = parser.parse_sync(str(fix_file))
                        chunks = chunker.chunk_document(parsed_doc, document_id=fix_file.name)
                        all_chunks.extend(chunks)
                    except Exception as pe:
                        print(f"[!] Error parsing fixture {fix_file.name}: {pe}")

        bm25_index.index_chunks(all_chunks)
        print(f"[*] Ingested {len(all_chunks)} chunks from {len(list(fixtures_dir.glob('*')))} fixtures into InMemoryBM25Index.")
        return bm25_index, "retrieval-memory-bm25", "disabled"

    elif profile == "qdrant-local":
        if not check_qdrant_health():
            raise RuntimeError(
                "Qdrant local instance at localhost:6333 is unreachable. "
                "Please start the Qdrant container or select '--profile memory'."
            )

        from app.services.embedding.deterministic_hash import DeterministicHashEmbeddingProvider
        from app.services.retrieval.qdrant_hybrid import QdrantHybridRetriever
        from app.repositories.vector.qdrant_client import QdrantVectorRepository

        parser = FastFallbackParser()
        chunker = TableAwareChunker(max_chunk_chars=800, chunk_overlap_chars=100)
        embedding_provider = DeterministicHashEmbeddingProvider(dimension=1024)
        repo = QdrantVectorRepository(collection_name="selnikel_benchmark_test")

        all_chunks = []
        if fixtures_dir.exists():
            for fix_file in sorted(fixtures_dir.glob("*")):
                if fix_file.is_file() and fix_file.suffix.lower() in [".pdf", ".docx", ".txt"]:
                    try:
                        parsed_doc = parser.parse_sync(str(fix_file))
                        chunks = chunker.chunk_document(parsed_doc, document_id=fix_file.name)
                        all_chunks.extend(chunks)
                    except Exception as pe:
                        print(f"[!] Error parsing fixture {fix_file.name}: {pe}")

        asyncio.run(repo.recreate_collection_with_schema(dimension=1024))
        asyncio.run(repo.upsert_chunks(all_chunks, embedding_provider))
        retriever = QdrantHybridRetriever(vector_repo=repo, embedding_provider=embedding_provider)
        print(f"[*] Ingested {len(all_chunks)} chunks into local Qdrant collection 'selnikel_benchmark_test'.")
        return retriever, "retrieval-qdrant-local-hybrid", "local_only"

    else:
        raise ValueError(f"Unknown retrieval profile: '{profile}'. Supported: 'memory', 'qdrant-local'.")


def run_benchmark(
    mode: str = "offline-retrieval",
    profile: str = "memory",
    dataset_path: Optional[Path] = None,
    category_filter: Optional[str] = None,
    output_path: Optional[Path] = None,
    base_dir: Optional[Path] = None,
    overwrite_report: bool = True,
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
    git_hash = get_git_commit(workspace_dir) or get_git_commit(backend_dir)

    # 1. Dataset Validation
    is_valid, validation_errors = validate_dataset_file(
        ds_file, schema_path=schema_file, verify_files_dir=fixtures_dir, manifest_path=manifest_file
    )
    if not is_valid:
        print(f"[!] Dataset validation failed with {len(validation_errors)} errors:")
        for err in validation_errors:
            print(f"    - {err}")
        empty_report = EvaluationRunReport(
            run_id=run_id,
            execution_mode=mode,
            status="FAILED",
            gate_status="FAILED",
            gate_failure_reasons=validation_errors[:5],
            dataset_sha256=dataset_sha,
            manifest_sha256=manifest_sha,
            git_commit=git_hash,
            executed_at=datetime.now(timezone.utc).isoformat(),
            duration_seconds=round(time.time() - start_time, 2),
            total_questions=0,
            passed_questions=0,
        )
        write_atomic_json(final_output_path, empty_report.model_dump(), overwrite=overwrite_report)
        return 1, empty_report, final_output_path

    evaluator = RAGBenchmarkEvaluator(dataset_path=ds_file)
    questions = evaluator.questions

    if category_filter:
        questions = [q for q in questions if q.category == category_filter]
        print(f"[*] Filtered questions by category '{category_filter}': {len(questions)} items.")

    # 2. Execute by Mode
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
        write_atomic_json(final_output_path, report.model_dump(), overwrite=overwrite_report)
        exit_code = 0 if report.gate_status == "PASSED" else 1
        return exit_code, report, final_output_path

    elif mode == "offline-retrieval":
        try:
            retriever, model_name, network_access = build_retrieval_index(profile, fixtures_dir)
        except Exception as build_err:
            print(f"[!] Failed to initialize retriever profile '{profile}': {build_err}")
            duration = time.time() - start_time
            report = EvaluationRunReport(
                run_id=run_id,
                execution_mode="offline-retrieval",
                status="FAILED",
                gate_status="FAILED",
                gate_failure_reasons=[str(build_err)],
                dataset_version="1.0.0",
                prompt_version=PROMPT_VERSION,
                prompt_sha256=prompt_sha,
                dataset_sha256=dataset_sha,
                manifest_sha256=manifest_sha,
                git_commit=git_hash,
                model_name=f"retrieval-{profile}-failed",
                oracle_mock_used=False,
                network_access="disabled",
                executed_at=datetime.now(timezone.utc).isoformat(),
                duration_seconds=round(duration, 2),
                total_questions=len(questions),
                passed_questions=0,
            )
            write_atomic_json(final_output_path, report.model_dump(), overwrite=overwrite_report)
            return 1, report, final_output_path

        results = []
        for q in questions:
            if hasattr(retriever, "search_sync"):
                retrieved = retriever.search_sync(q.question, top_k=5)
            elif hasattr(retriever, "search"):
                res = retriever.search(q.question, top_k=5)
                if asyncio.iscoroutine(res):
                    retrieved = asyncio.run(res)
                else:
                    retrieved = res
            else:
                retrieved = []

            item_res = evaluator.evaluate_retrieval_only(q, retrieved)
            results.append(item_res)

        duration = time.time() - start_time
        report = evaluator.generate_run_report(
            results,
            execution_mode="offline-retrieval",
            status="COMPLETED",
            dataset_version="1.0.0",
            model_name=model_name,
            prompt_version=PROMPT_VERSION,
            prompt_sha256=prompt_sha,
            dataset_sha256=dataset_sha,
            manifest_sha256=manifest_sha,
            git_commit=git_hash,
            oracle_mock_used=False,
            network_access=network_access,
            duration_seconds=duration,
            run_id=run_id,
        )
        write_atomic_json(final_output_path, report.model_dump(), overwrite=overwrite_report)
        exit_code = 0 if report.gate_status == "PASSED" else 1
        return exit_code, report, final_output_path

    elif mode == "full-rag":
        # Check if real generator is available and healthy
        openai_key = os.environ.get("OPENAI_API_KEY")
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        local_llm_url = os.environ.get("LOCAL_LLM_URL")

        generator_available = False
        generator_type = "none"
        net_access = "disabled"

        if openai_key and len(openai_key.strip()) > 10:
            generator_available = True
            generator_type = "openai"
            net_access = "external"
        elif anthropic_key and len(anthropic_key.strip()) > 10:
            generator_available = True
            generator_type = "anthropic"
            net_access = "external"
        elif local_llm_url:
            if check_local_llm_health(local_llm_url):
                generator_available = True
                generator_type = "local_llm"
                net_access = "local_only"
            else:
                print(f"[!] LOCAL_LLM_URL specified ({local_llm_url}) but server is unreachable.")

        if not generator_available:
            print("[!] Mode full-rag requested but no live generator is available or reachable.")
            print("[!] Full-RAG execution requires live LLM generation (mocking disallowed).")
            print("[!] Marking benchmark run status as SKIPPED with exit code 0.")
            duration = time.time() - start_time
            report = EvaluationRunReport(
                run_id=run_id,
                execution_mode="full-rag",
                status="SKIPPED",
                gate_status="SKIPPED",
                gate_failure_reasons=["No live/reachable LLM generator configured."],
                dataset_version="1.0.0",
                prompt_version=PROMPT_VERSION,
                prompt_sha256=prompt_sha,
                dataset_sha256=dataset_sha,
                manifest_sha256=manifest_sha,
                git_commit=git_hash,
                model_name=f"full-rag-{generator_type}",
                oracle_mock_used=False,
                network_access=net_access,
                executed_at=datetime.now(timezone.utc).isoformat(),
                duration_seconds=round(duration, 2),
                total_questions=len(questions),
                passed_questions=0,
            )
            write_atomic_json(final_output_path, report.model_dump(), overwrite=overwrite_report)
            return 0, report, final_output_path

        # Live generator is available -> Execute full RAG pipeline
        try:
            from app.services.rag.engine import DeterministicRAGEngine
            from app.services.llm.factory import get_llm_provider

            retriever, _, _ = build_retrieval_index(profile, fixtures_dir)
            llm_provider = get_llm_provider()
            rag_engine = DeterministicRAGEngine(retriever=retriever, llm_provider=llm_provider)

            results = []
            for q in questions:
                gen_output, chunks = asyncio.run(rag_engine.query_with_retrieval(q.question))
                item_res = evaluator.evaluate_single(q, gen_output, chunks)
                results.append(item_res)

            duration = time.time() - start_time
            report = evaluator.generate_run_report(
                results,
                execution_mode="full-rag",
                status="COMPLETED",
                dataset_version="1.0.0",
                model_name=f"full-rag-{generator_type}",
                prompt_version=PROMPT_VERSION,
                prompt_sha256=prompt_sha,
                dataset_sha256=dataset_sha,
                manifest_sha256=manifest_sha,
                git_commit=git_hash,
                oracle_mock_used=False,
                network_access=net_access,
                duration_seconds=duration,
                run_id=run_id,
            )
            write_atomic_json(final_output_path, report.model_dump(), overwrite=overwrite_report)
            exit_code = 0 if report.gate_status == "PASSED" else 1
            return exit_code, report, final_output_path

        except Exception as rag_err:
            print(f"[!] Full-RAG execution encountered error: {rag_err}")
            duration = time.time() - start_time
            report = EvaluationRunReport(
                run_id=run_id,
                execution_mode="full-rag",
                status="FAILED",
                gate_status="FAILED",
                gate_failure_reasons=[str(rag_err)],
                dataset_version="1.0.0",
                prompt_version=PROMPT_VERSION,
                prompt_sha256=prompt_sha,
                dataset_sha256=dataset_sha,
                manifest_sha256=manifest_sha,
                git_commit=git_hash,
                model_name=f"full-rag-{generator_type}-failed",
                oracle_mock_used=False,
                network_access=net_access,
                executed_at=datetime.now(timezone.utc).isoformat(),
                duration_seconds=round(duration, 2),
                total_questions=len(questions),
                passed_questions=0,
            )
            write_atomic_json(final_output_path, report.model_dump(), overwrite=overwrite_report)
            return 1, report, final_output_path

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
        print(f"  Execution Status  : {report.status}")
        print(f"  Quality Gate      : {report.gate_status}")
        if report.gate_failure_reasons:
            print(f"  Gate Reasons      : {', '.join(report.gate_failure_reasons)}")
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