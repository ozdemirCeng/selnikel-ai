"""
Backwards-compatibility shim pointing to production evaluator package at app.services.evaluation.
"""
from app.services.evaluation.evaluator import RAGBenchmarkEvaluator
from app.domain.contracts.evaluation import BenchmarkQuestion, ExpectedEvidence, MetricResult

# Alias for backwards compatibility
EvaluationItem = BenchmarkQuestion

__all__ = [
    "RAGBenchmarkEvaluator",
    "BenchmarkQuestion",
    "ExpectedEvidence",
    "MetricResult",
    "EvaluationItem",
]
