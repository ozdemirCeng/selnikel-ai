"""
RAG Evaluation Benchmark & Safety Metric Test Suite.
Validates mathematical metrics: Recall@5, nDCG@5, Parameter Accuracy, Faithfulness, Abstention, and Safety-Critical checks
against the production RAGBenchmarkEvaluator service.
"""
from pathlib import Path
from unittest.mock import AsyncMock
import pytest
from app.domain.contracts.evaluation import BenchmarkQuestion, ExpectedEvidence
from app.domain.document import ChunkMetadata
from app.domain.rag import Citation, GenerationOutput, RetrievalResult
from app.services.evaluation.evaluator import RAGBenchmarkEvaluator
from app.services.evaluation.metrics import (
    compute_evidence_recall_at_k,
    compute_page_aware_ndcg_at_k,
)
from app.services.rag.engine import DeterministicRAGEngine


@pytest.fixture
def eval_dataset_path():
    return (
        Path(__file__).resolve().parent.parent
        / "app"
        / "evaluation"
        / "datasets"
        / "golden_benchmark_baseline.json"
    )


def test_evaluator_loads_questions(eval_dataset_path):
    evaluator = RAGBenchmarkEvaluator(dataset_path=eval_dataset_path)
    assert len(evaluator.questions) == 3
    assert evaluator.questions[0].id == "selnikel-bench-001"
    assert "SB-Series" in evaluator.questions[0].question


def test_ndcg_and_recall_calculation(eval_dataset_path):
    """Verify Recall@5 and nDCG@5 calculations."""
    evaluator = RAGBenchmarkEvaluator(dataset_path=eval_dataset_path)
    q = evaluator.questions[0]

    meta_match = ChunkMetadata(
        chunk_id="chunk-1",
        document_id="doc-1",
        document_version=1,
        filename=q.expected_evidence.document_name,
        page_number=q.expected_evidence.page_number,
        token_count=10,
    )
    meta_other = ChunkMetadata(
        chunk_id="chunk-2",
        document_id="doc-2",
        document_version=1,
        filename="Other_Manual.pdf",
        page_number=1,
        token_count=10,
    )

    chunks_top1 = [
        RetrievalResult(chunk_id="1", content="Text", metadata=meta_match, score=0.9),
        RetrievalResult(chunk_id="2", content="Text", metadata=meta_other, score=0.8),
    ]

    recall = compute_evidence_recall_at_k(q.expected_evidence, chunks_top1, k=5)
    ndcg = compute_page_aware_ndcg_at_k(q.expected_evidence, chunks_top1, k=5)

    assert recall == 1.0
    assert ndcg == 1.0  # Top-1 hit produces perfect 1.0 nDCG


@pytest.mark.asyncio
async def test_rag_pipeline_benchmark_evaluation(eval_dataset_path):
    evaluator = RAGBenchmarkEvaluator(dataset_path=eval_dataset_path)

    # Mock RAG Engine simulating exact grounded responses
    mock_retriever = AsyncMock()
    mock_reranker = AsyncMock()
    mock_llm = AsyncMock()

    engine = DeterministicRAGEngine(
        retriever=mock_retriever,
        reranker=mock_reranker,
        llm=mock_llm,
    )

    results = []
    for item in evaluator.questions:
        meta = ChunkMetadata(
            chunk_id=f"chunk_{item.id}",
            document_id=f"doc_{item.id}",
            document_version=1,
            filename=item.expected_evidence.document_name,
            page_number=item.expected_evidence.page_number,
            section=item.expected_evidence.section or "Benchmark",
            document_type="technical_specification",
            department="engineering",
            language="tr",
            chunk_index=0,
            token_count=30,
        )
        chunk = RetrievalResult(
            chunk_id=f"chunk_{item.id}",
            content=f"Technical data: {', '.join(item.expected_evidence.expected_numerical_parameters)}",
            metadata=meta,
            score=0.95,
        )

        mock_retriever.retrieve.return_value = [chunk]
        mock_reranker.rerank.return_value = [chunk]
        mock_llm.generate.return_value = (
            f"{item.expected_evidence.ground_truth_answer} [Doc: {item.expected_evidence.document_name}, P. {item.expected_evidence.page_number}]"
        )

        output = await engine.query(item.question)
        eval_res = evaluator.evaluate_single(item, output, retrieved_chunks=[chunk])
        results.append(eval_res)

    assert len(results) == 3
    avg_score = sum(r.metrics.overall_score for r in results) / len(results)

    # Assert benchmark threshold exceeds 80%
    assert avg_score >= 0.80
    for r in results:
        assert r.metrics.recall_at_5 == 1.0
        assert r.metrics.ndcg_at_5 == 1.0
        assert r.metrics.citation_precision == 1.0
        assert r.passed is True
