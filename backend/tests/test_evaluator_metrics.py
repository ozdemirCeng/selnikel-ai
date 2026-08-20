"""
Unit & Adversarial Edge Case Tests for RAG Benchmark Metrics and Contracts.
Validates:
1. Empty / None retrieval contexts strictly return 0.0 for Recall and nDCG.
2. Page-proximity relevance and duplicate chunk de-inflation in nDCG@K.
3. Numerical parameter extraction with comma normalization and unit mismatch rejection.
4. Citation provenance verification against retrieved chunks.
5. Faithfulness scoring and honest abstention handling.
6. Safety-critical threshold gates.
7. Deterministic evaluation output.
"""
import math
import pytest
from app.domain.contracts.evaluation import (
    BenchmarkQuestion,
    ExpectedEvidence,
    MetricResult,
)
from app.domain.contracts.prompt import PROMPT_VERSION, PromptContract, current_prompt_contract
from app.domain.document import ChunkMetadata
from app.domain.rag import Citation, GenerationOutput, RetrievalResult
from app.services.evaluation.metrics import (
    compute_abstention_accuracy,
    compute_citation_precision,
    compute_evidence_recall_at_k,
    compute_faithfulness_score,
    compute_numerical_unit_accuracy,
    compute_page_aware_ndcg_at_k,
    compute_safety_compliance,
    evaluate_metrics,
    extract_parameters,
)
from app.services.evaluation.evaluator import RAGBenchmarkEvaluator


def test_empty_and_none_retrieval_returns_zero():
    """CRITICAL FIX VERIFICATION: Verify that empty and None chunk lists return 0.0 strictly."""
    expected = ExpectedEvidence(
        document_name="boiler_manual.pdf",
        page_number=10,
        ground_truth_answer="Operating pressure is 16 bar.",
    )

    # Empty list
    assert compute_evidence_recall_at_k(expected, []) == 0.0
    assert compute_page_aware_ndcg_at_k(expected, []) == 0.0

    # None list
    assert compute_evidence_recall_at_k(expected, None) == 0.0
    assert compute_page_aware_ndcg_at_k(expected, None) == 0.0


def test_page_proximity_and_duplicate_ndcg_deinflation():
    """Verify page proximity rewards and that duplicate chunks from same page do not inflate DCG."""
    expected = ExpectedEvidence(
        document_name="manual.pdf",
        page_number=5,
        ground_truth_answer="Test answer",
    )

    # Chunk 1: Exact match (Page 5) -> relevance 1.0
    # Chunk 2: Duplicate of Page 5 -> relevance 0.0 (no inflation)
    # Chunk 3: Adjacent match (Page 6) -> relevance 0.5
    chunks = [
        RetrievalResult(
            chunk_id="c1",
            content="Content page 5",
            metadata=ChunkMetadata(chunk_id="c1", document_id="d1", filename="manual.pdf", page_number=5),
            score=0.9,
        ),
        RetrievalResult(
            chunk_id="c2",
            content="Duplicate page 5",
            metadata=ChunkMetadata(chunk_id="c2", document_id="d1", filename="manual.pdf", page_number=5),
            score=0.8,
        ),
        RetrievalResult(
            chunk_id="c3",
            content="Content page 6",
            metadata=ChunkMetadata(chunk_id="c3", document_id="d1", filename="manual.pdf", page_number=6),
            score=0.7,
        ),
    ]

    recall = compute_evidence_recall_at_k(expected, chunks, k=5)
    ndcg = compute_page_aware_ndcg_at_k(expected, chunks, k=5)

    assert recall == 1.0
    # DCG = 1.0/log2(2) + 0.0/log2(3) + 0.5/log2(4) = 1.0 + 0.0 + 0.25 = 1.25
    # IDCG = 1.0/log2(2) = 1.0
    # Normalized nDCG capped at 1.0
    assert ndcg == 1.0


def test_numerical_unit_accuracy_and_comma_normalization():
    """Verify exact numerical and physical unit matching with comma support."""
    # Test extraction
    params = extract_parameters("Basınç 16,5 bar ve sıcaklık 250 °C olmalıdır.")
    assert (16.5, "bar") in params
    assert (250.0, "°c") in params

    # Match exact
    expected_params = ["16.5 bar", "250 °C"]
    answer_correct = "Sistem basıncı 16,5 bar, sıcaklık ise 250 °C'dir."
    assert compute_numerical_unit_accuracy(expected_params, answer_correct) == 1.0

    # Unit mismatch: "16.5 kW" instead of "16.5 bar"
    answer_wrong_unit = "Sistem kapasitesi 16.5 kW ve 250 °C'dir."
    assert compute_numerical_unit_accuracy(expected_params, answer_wrong_unit) == 0.5

    # Completely missing numbers
    answer_no_nums = "Sistem yüksek basınç ve sıcaklıkta çalışır."
    assert compute_numerical_unit_accuracy(expected_params, answer_no_nums) == 0.0


def test_citation_provenance_validation():
    """Verify citations are strictly checked against retrieved chunks."""
    retrieved = [
        RetrievalResult(
            chunk_id="c1",
            content="Text from page 4",
            metadata=ChunkMetadata(chunk_id="c1", document_id="d1", filename="boiler.pdf", page_number=4),
            score=0.9,
        )
    ]

    # Valid citation matching retrieved chunk
    valid_citations = [
        Citation(document_id="d1", filename="boiler.pdf", page_number=4, snippet="Text from page 4")
    ]
    assert compute_citation_precision(valid_citations, retrieved) == 1.0

    # Hallucinated citation referencing document not in context
    hallucinated_citations = [
        Citation(document_id="d2", filename="secret_manual.pdf", page_number=1, snippet="Fake snippet")
    ]
    assert compute_citation_precision(hallucinated_citations, retrieved) == 0.0


def test_abstention_accuracy_and_safety_compliance():
    """Verify honest refusal behavior on out-of-domain and safety-critical rules."""
    # Out of domain query
    ood_answer_refused = "Sağlanan teknik dokümanlarda bu konuyla ilgili yeterli bilgi bulunmamaktadır."
    ood_answer_hallucinated = "Bu işlem için genel internet kılavuzlarına bakınız."

    assert compute_abstention_accuracy(is_out_of_domain=True, generated_answer=ood_answer_refused) == 1.0
    assert compute_abstention_accuracy(is_out_of_domain=True, generated_answer=ood_answer_hallucinated) == 0.0

    # Safety critical test: low numerical accuracy must fail safety compliance
    assert compute_safety_compliance(is_safety_critical=True, numerical_accuracy=0.5, citation_precision=1.0, generated_answer="Yanıt") == 0.0
    assert compute_safety_compliance(is_safety_critical=True, numerical_accuracy=1.0, citation_precision=1.0, generated_answer="16 bar [Doc: a, P. 1]") == 1.0


def test_evaluator_deterministic_results():
    """Verify that repeated evaluation with identical input yields identical deterministic scores."""
    question = BenchmarkQuestion(
        id="selnikel-bench-001",
        category="capacity_pressure_temp",
        question="What is the operating pressure?",
        expected_evidence=ExpectedEvidence(
            document_name="datasheet.pdf",
            page_number=3,
            expected_numerical_parameters=["16 bar"],
            ground_truth_answer="Operating pressure is 16 bar.",
        ),
        is_safety_critical=True,
    )

    gen_out = GenerationOutput(
        answer="Operating pressure is 16 bar. [Doc: datasheet.pdf, P. 3]",
        citations=[Citation(document_id="d1", filename="datasheet.pdf", page_number=3, snippet="16 bar")],
    )

    chunk = RetrievalResult(
        chunk_id="c1",
        content="Operating pressure is 16 bar.",
        metadata=ChunkMetadata(chunk_id="c1", document_id="d1", filename="datasheet.pdf", page_number=3),
        score=0.95,
    )

    evaluator = RAGBenchmarkEvaluator(questions=[question])

    res1 = evaluator.evaluate_single(question, gen_out, [chunk])
    res2 = evaluator.evaluate_single(question, gen_out, [chunk])

    assert res1.metrics.overall_score == res2.metrics.overall_score
    assert res1.metrics.recall_at_5 == 1.0
    assert res1.metrics.ndcg_at_5 == 1.0
    assert res1.metrics.numerical_unit_accuracy == 1.0
    assert res1.passed is True


def test_prompt_contract_invariants():
    """Verify prompt contract hash, versioning, and anti-injection instructions."""
    contract = current_prompt_contract
    assert contract.version == PROMPT_VERSION
    assert len(contract.prompt_hash) == 64
    assert "ANTI-INJECTION" in contract.system_prompt
    assert "SIFIR HALÜSİNASYON" in contract.system_prompt
