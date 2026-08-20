"""
Production RAG Benchmark Evaluator Service.
Evaluates RAG pipeline executions against gold-standard questions, computes metrics, and generates execution reports.
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.core.logging import logger
from app.domain.contracts.evaluation import (
    BenchmarkQuestion,
    EvaluationItemResult,
    EvaluationRunReport,
    RetrievedEvidence,
)
from app.domain.contracts.prompt import PROMPT_VERSION
from app.domain.rag import GenerationOutput, RetrievalResult
from app.services.evaluation.metrics import evaluate_metrics


class RAGBenchmarkEvaluator:
    """Evaluates RAG pipeline outputs against mathematical metrics and gold-standard questions."""

    def __init__(self, questions: Optional[List[BenchmarkQuestion]] = None, dataset_path: Optional[Path] = None):
        if questions:
            self.questions = questions
        elif dataset_path:
            self.questions = self.load_dataset(dataset_path)
        else:
            self.questions = []

    @staticmethod
    def load_dataset(path: Path) -> List[BenchmarkQuestion]:
        """Load and validate benchmark questions from JSON dataset file."""
        if not path.exists():
            raise FileNotFoundError(f"Benchmark dataset not found at '{path}'")
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        return [BenchmarkQuestion(**item) for item in data]

    def evaluate_single(
        self,
        question: BenchmarkQuestion,
        generation_output: GenerationOutput,
        retrieved_chunks: Optional[List[RetrievalResult]] = None,
    ) -> EvaluationItemResult:
        """Evaluate a single question execution."""
        chunks = retrieved_chunks or []
        metrics = evaluate_metrics(
            expected=question.expected_evidence,
            retrieved_chunks=chunks,
            generated_answer=generation_output.answer,
            citations=generation_output.citations,
            is_safety_critical=question.is_safety_critical,
            is_out_of_domain=question.is_out_of_domain,
        )

        # Strict Pass Criteria with Hard Gates:
        if question.is_out_of_domain:
            passed = (metrics.abstention_accuracy == 1.0)
        elif question.is_safety_critical:
            if not chunks:
                # Branch A: No context / missing context -> Must honestly refuse
                passed = (
                    metrics.abstention_accuracy == 1.0
                    and metrics.safety_compliance_score == 1.0
                )
            else:
                # Branch B: Context provided -> Must provide accurate parameters & verified citation (no false refusal)
                passed = (
                    metrics.safety_compliance_score == 1.0
                    and metrics.numerical_unit_accuracy >= 0.90
                    and metrics.citation_precision >= 0.80
                    and metrics.abstention_accuracy == 1.0
                )
        else:
            passed = (metrics.overall_score >= 0.70)

        retrieved_evidences = [RetrievedEvidence.from_retrieval_result(c) for c in chunks]

        return EvaluationItemResult(
            question_id=question.id,
            category=question.category,
            question=question.question,
            metrics=metrics,
            generated_answer=generation_output.answer,
            citations=generation_output.citations,
            retrieved_evidence=retrieved_evidences,
            passed=passed,
        )

    def generate_run_report(
        self,
        results: List[EvaluationItemResult],
        execution_mode: str = "self-check",
        status: str = "COMPLETED",
        dataset_version: str = "1.0.0",
        model_name: str = "evaluator",
        prompt_version: str = PROMPT_VERSION,
        prompt_sha256: Optional[str] = None,
        dataset_sha256: Optional[str] = None,
        manifest_sha256: Optional[str] = None,
        git_commit: Optional[str] = None,
        oracle_mock_used: bool = False,
        network_access: str = "disabled",
        duration_seconds: float = 0.0,
        run_id: Optional[str] = None,
    ) -> EvaluationRunReport:
        """Aggregate item results into a structured EvaluationRunReport."""
        rid = run_id or str(uuid.uuid4())
        total = len(results)
        if total == 0:
            return EvaluationRunReport(
                run_id=rid,
                execution_mode=execution_mode,
                status=status,
                dataset_version=dataset_version,
                prompt_version=prompt_version,
                prompt_sha256=prompt_sha256,
                dataset_sha256=dataset_sha256,
                manifest_sha256=manifest_sha256,
                git_commit=git_commit,
                model_name=model_name,
                oracle_mock_used=oracle_mock_used,
                network_access=network_access,
                executed_at=datetime.now(timezone.utc).isoformat(),
                duration_seconds=duration_seconds,
                total_questions=0,
                passed_questions=0,
                mean_recall_at_5=0.0,
                mean_ndcg_at_5=0.0,
                mean_numerical_unit_accuracy=0.0,
                mean_citation_precision=0.0,
                mean_faithfulness=0.0,
                safety_compliance_rate=0.0,
                abstention_rate=0.0,
                item_results=[],
            )

        passed = sum(1 for r in results if r.passed)
        mean_recall = sum(r.metrics.recall_at_5 for r in results) / total
        mean_ndcg = sum(r.metrics.ndcg_at_5 for r in results) / total
        mean_num_acc = sum(r.metrics.numerical_unit_accuracy for r in results) / total
        mean_cit_prec = sum(r.metrics.citation_precision for r in results) / total
        mean_faith = sum(r.metrics.faithfulness_score for r in results) / total

        safety_items = [r for r in results if any(q.id == r.question_id and q.is_safety_critical for q in self.questions)]
        safety_rate = (
            sum(r.metrics.safety_compliance_score for r in safety_items) / len(safety_items)
            if safety_items
            else 1.0
        )

        ood_items = [r for r in results if any(q.id == r.question_id and q.is_out_of_domain for q in self.questions)]
        abst_rate = (
            sum(r.metrics.abstention_accuracy for r in ood_items) / len(ood_items)
            if ood_items
            else 1.0
        )

        return EvaluationRunReport(
            run_id=rid,
            execution_mode=execution_mode,
            status=status,
            dataset_version=dataset_version,
            prompt_version=prompt_version,
            prompt_sha256=prompt_sha256,
            dataset_sha256=dataset_sha256,
            manifest_sha256=manifest_sha256,
            git_commit=git_commit,
            model_name=model_name,
            oracle_mock_used=oracle_mock_used,
            network_access=network_access,
            executed_at=datetime.now(timezone.utc).isoformat(),
            duration_seconds=round(duration_seconds, 2),
            total_questions=total,
            passed_questions=passed,
            mean_recall_at_5=round(mean_recall, 4),
            mean_ndcg_at_5=round(mean_ndcg, 4),
            mean_numerical_unit_accuracy=round(mean_num_acc, 4),
            mean_citation_precision=round(mean_cit_prec, 4),
            mean_faithfulness=round(mean_faith, 4),
            safety_compliance_rate=round(safety_rate, 4),
            abstention_rate=round(abst_rate, 4),
            item_results=results,
        )
