"""
RAG Evaluation Benchmark & Safety Metric Test Suite
Validates mathematical metrics: Recall@5, nDCG@5, Faithfulness, Abstention, and Safety-Critical checks.
"""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock
from app.domain.document import ChunkMetadata
from app.domain.rag import Citation, GenerationOutput, RetrievalResult
from app.services.rag.engine import DeterministicRAGEngine
from tests.evaluation.evaluator import RAGBenchmarkEvaluator, EvaluationItem

@pytest.fixture
def eval_json_path():
    return Path(__file__).parent / "evaluation" / "questions.json"


def test_evaluator_loads_questions(eval_json_path):
    evaluator = RAGBenchmarkEvaluator(eval_json_path)
    assert len(evaluator.questions) == 3
    assert evaluator.questions[0].id == "eval_001"
    assert "SB-Series" in evaluator.questions[0].question


def test_ndcg_and_recall_calculation(eval_json_path):
    """Verify Recall@5 and nDCG@5 calculations."""
    evaluator = RAGBenchmarkEvaluator(eval_json_path)
    item = evaluator.questions[0]

    meta_match = ChunkMetadata(
        chunk_id="chunk-1",
        document_id="doc-1",
        document_version=1,
        filename=item.expected_document,
        page_number=item.expected_page,
        token_count=10,
        is_table=False
    )
    meta_other = ChunkMetadata(
        chunk_id="chunk-2",
        document_id="doc-2",
        document_version=1,
        filename="Other_Manual.pdf",
        page_number=1,
        token_count=10,
        is_table=False
    )

    chunks_top1 = [
        RetrievalResult(chunk_id="1", content="Text", metadata=meta_match, score=0.9),
        RetrievalResult(chunk_id="2", content="Text", metadata=meta_other, score=0.8),
    ]

    recall = evaluator.compute_recall_at_k(item, chunks_top1, k=5)
    ndcg = evaluator.compute_ndcg_at_k(item, chunks_top1, k=5)

    assert recall == 1.0
    assert ndcg == 1.0  # Top-1 hit produces perfect 1.0 nDCG


@pytest.mark.asyncio
async def test_rag_pipeline_benchmark_evaluation(eval_json_path):
    evaluator = RAGBenchmarkEvaluator(eval_json_path)

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
            filename=item.expected_document,
            page_number=item.expected_page,
            section="Benchmark",
            document_type="technical_specification",
            department="engineering",
            language="tr",
            chunk_index=0,
            token_count=30,
        )
        chunk = RetrievalResult(
            chunk_id=f"chunk_{item.id}",
            content=f"Technical data: {', '.join(item.expected_keywords)}",
            metadata=meta,
            score=0.95,
        )

        mock_retriever.retrieve.return_value = [chunk]
        mock_reranker.rerank.return_value = [chunk]
        mock_llm.generate.return_value = (
            f"{item.ground_truth_answer} [Belge: {item.expected_document}, Sayfa: {item.expected_page}]"
        )

        output = await engine.query(item.question)
        eval_res = evaluator.evaluate_output(item, output, retrieved_chunks=[chunk])
        results.append(eval_res)

    assert len(results) == 3
    avg_score = sum(r.overall_score for r in results) / len(results)
    
    # Assert benchmark threshold exceeds 85%
    assert avg_score >= 0.85
    for r in results:
        assert r.recall_at_k == 1.0
        assert r.ndcg_at_k == 1.0
        assert r.citation_precision == 1.0
        assert r.safety_critical_passed is True
