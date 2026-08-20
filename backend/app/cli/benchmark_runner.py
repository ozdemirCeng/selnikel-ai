"""
CLI Command: Execute RAG Benchmark Evaluation Run.
Usage:
    python -m app.cli.benchmark_runner [--dataset path/to/dataset.json] [--output path/to/report.json]
"""
import argparse
import json
import sys
from pathlib import Path
from app.domain.contracts.evaluation import BenchmarkQuestion
from app.domain.rag import Citation, GenerationOutput, RetrievalResult
from app.services.evaluation.evaluator import RAGBenchmarkEvaluator


def main():
    parser = argparse.ArgumentParser(description="Run Selnikel AI RAG Benchmark Evaluation Suite")
    parser.add_argument("--dataset", type=str, default=None, help="Path to golden benchmark JSON dataset")
    parser.add_argument("--output", type=str, default=None, help="Path to save evaluation run report JSON")
    args = parser.parse_args()

    backend_dir = Path(__file__).resolve().parent.parent
    if args.dataset:
        dataset_path = Path(args.dataset)
    else:
        dataset_path = backend_dir / "evaluation" / "datasets" / "golden_benchmark_baseline.json"

    if args.output:
        output_path = Path(args.output)
    else:
        reports_dir = backend_dir / "evaluation" / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        output_path = reports_dir / "baseline_selfcheck_v1.json"

    print(f"[*] Loading benchmark questions from: {dataset_path}")
    evaluator = RAGBenchmarkEvaluator(dataset_path=dataset_path)
    print(f"[*] Loaded {len(evaluator.questions)} benchmark items.")

    results = []
    for q in evaluator.questions:
        print(f"    -> Evaluating question [{q.id}]: {q.question[:60]}...")
        # Evaluator self-check mode: simulates exact grounded answer with valid citation
        simulated_output = GenerationOutput(
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

        from app.domain.document import ChunkMetadata
        simulated_chunk = RetrievalResult(
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

        item_result = evaluator.evaluate_single(q, simulated_output, [simulated_chunk])
        results.append(item_result)

    report = evaluator.generate_run_report(
        results,
        dataset_version="1.0.0",
        model_name="evaluator-selfcheck-reference-v1",
    )

    report_dict = report.model_dump()
    report_dict["execution_mode"] = "evaluator_self_check"
    report_dict["evaluation_note"] = "Self-check verification of mathematical evaluator formulas using ground-truth pairs (not live retrieval benchmark)."

    with open(output_path, "w", encoding="utf-8") as rf:
        json.dump(report_dict, rf, indent=2, ensure_ascii=False)

    print(f"[+] Evaluator self-check run completed successfully.")
    print(f"[+] Mode: {report_dict['execution_mode']}")
    print(f"[+] Total Questions: {report.total_questions} | Passed: {report.passed_questions}")
    print(f"[+] Mean Recall@5: {report.mean_recall_at_5:.4f}")
    print(f"[+] Mean nDCG@5: {report.mean_ndcg_at_5:.4f}")
    print(f"[+] Mean Numerical/Unit Accuracy: {report.mean_numerical_unit_accuracy:.4f}")
    print(f"[+] Mean Citation Precision: {report.mean_citation_precision:.4f}")
    print(f"[+] Mean Faithfulness: {report.mean_faithfulness:.4f}")
    print(f"[+] Report saved to: {output_path}")


if __name__ == "__main__":
    main()
