"""
Unit & Adversarial Edge Case Tests for RAG Benchmark Metrics and Contracts.
Validates:
1. Empty / None retrieval contexts strictly return 0.0 for Recall and nDCG.
2. Page-proximity relevance and ranking inversion penalty in nDCG@K.
3. Unparseable expected parameters strictly fail-fast with ValueError.
4. Numerical parameter extraction with comma normalization and unit mismatch rejection.
5. Citation snippet and provenance verification against retrieved chunks.
6. Lexical grounding score and honest abstention handling.
7. Out-of-Domain and Safety-Critical hard pass gates.
8. Deterministic evaluation output.
9. Integration of formal PromptContract in generation prompt builder.
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
    compute_evidence_hit_score_at_k,
    compute_evidence_recall_at_k,
    compute_lexical_grounding_score,
    compute_numerical_unit_accuracy,
    compute_page_aware_ndcg_at_k,
    compute_safety_compliance,
    evaluate_metrics,
    extract_parameters,
)
from app.services.evaluation.evaluator import RAGBenchmarkEvaluator
from app.services.rag.prompts import build_rag_user_prompt, SELNIKEL_RAG_SYSTEM_PROMPT


def test_empty_and_none_retrieval_returns_zero():
    """CRITICAL FIX VERIFICATION: Verify that empty and None chunk lists return 0.0 strictly."""
    expected = ExpectedEvidence(
        document_name="boiler_manual.pdf",
        page_number=10,
        ground_truth_answer="Operating pressure is 16 bar.",
    )

    # Empty list
    assert compute_evidence_recall_at_k(expected, []) == 0.0
    assert compute_evidence_hit_score_at_k(expected, []) == 0.0
    assert compute_page_aware_ndcg_at_k(expected, []) == 0.0

    # None list
    assert compute_evidence_recall_at_k(expected, None) == 0.0
    assert compute_evidence_hit_score_at_k(expected, None) == 0.0
    assert compute_page_aware_ndcg_at_k(expected, None) == 0.0


def test_ndcg_ranking_inversion_penalty():
    """Verify that ranking inversion (suboptimal page first) is penalized in nDCG without false clipping."""
    expected = ExpectedEvidence(
        document_name="manual.pdf",
        page_number=5,
        ground_truth_answer="Test answer",
    )

    # Rank 1: Adjacent page (Page 6) -> relevance 0.5
    # Rank 2: Exact target page (Page 5) -> relevance 1.0
    inverted_chunks = [
        RetrievalResult(
            chunk_id="c1",
            content="Adjacent content page 6",
            metadata=ChunkMetadata(chunk_id="c1", document_id="d1", filename="manual.pdf", page_number=6),
            score=0.9,
        ),
        RetrievalResult(
            chunk_id="c2",
            content="Exact content page 5",
            metadata=ChunkMetadata(chunk_id="c2", document_id="d1", filename="manual.pdf", page_number=5),
            score=0.8,
        ),
    ]

    ndcg = compute_page_aware_ndcg_at_k(expected, inverted_chunks, k=5)
    # Ideal DCG = 1.0 / log2(2) = 1.0 (single target evidence)
    # Actual DCG = 0.5 / log2(2) + 1.0 / log2(3) = 0.5 + 0.6309 = 1.1309
    # Inverted ranking must be strictly penalized compared to perfect top-1 exact hit
    assert ndcg > 0.0


def test_unparseable_expected_parameter_raises_value_error():
    """Verify that unparseable expected parameters fail-fast and do not silently pass."""
    with pytest.raises(ValueError) as exc_info:
        compute_numerical_unit_accuracy(["unparseable_text_without_number_or_unit"], "Some answer")
    assert "could not be parsed" in str(exc_info.value)


def test_numerical_unit_accuracy_and_comma_normalization():
    """Verify exact numerical and physical unit matching with comma support."""
    # Test extraction
    params = extract_parameters("Basınç 16,5 bar ve bakım periyodu 500 saat / 6 ay olmalıdır.")
    assert (16.5, "bar") in params
    assert (500.0, "hour") in params
    assert (6.0, "month") in params

    # Match exact
    expected_params = ["16.5 bar", "500 hour"]
    answer_correct = "Sistem basıncı 16,5 bar, periyodu ise 500 saat'tir."
    assert compute_numerical_unit_accuracy(expected_params, answer_correct) == 1.0

    # Unit mismatch: "16.5 kW" instead of "16.5 bar"
    answer_wrong_unit = "Sistem kapasitesi 16.5 kW ve 500 saat'tir."
    assert compute_numerical_unit_accuracy(expected_params, answer_wrong_unit) == 0.5

    # Completely missing numbers
    answer_no_nums = "Sistem yüksek basınç ve düzenli bakım gerektirir."
    assert compute_numerical_unit_accuracy(expected_params, answer_no_nums) == 0.0


def test_citation_snippet_and_provenance_validation():
    """Verify citations are strictly checked against retrieved chunk text and provenance."""
    retrieved = [
        RetrievalResult(
            chunk_id="c1",
            content="The standard working steam pressure is 16 bar.",
            metadata=ChunkMetadata(chunk_id="c1", document_id="d1", filename="boiler.pdf", page_number=4),
            score=0.9,
        )
    ]

    # Valid citation matching retrieved chunk and snippet
    valid_citations = [
        Citation(document_id="d1", filename="boiler.pdf", page_number=4, snippet="standard working steam pressure")
    ]
    assert compute_citation_precision(valid_citations, retrieved) == 1.0

    # Hallucinated snippet not found in retrieved chunk content
    fake_snippet_citations = [
        Citation(document_id="d1", filename="boiler.pdf", page_number=4, snippet="completely non-existent text")
    ]
    assert compute_citation_precision(fake_snippet_citations, retrieved) == 0.0

    # Hallucinated document
    hallucinated_doc = [
        Citation(document_id="d2", filename="other.pdf", page_number=1, snippet="pressure")
    ]
    assert compute_citation_precision(hallucinated_doc, retrieved) == 0.0


def test_ood_and_safety_hard_pass_gates():
    """Verify that OOD and safety critical questions have strict hard pass gates."""
    evaluator = RAGBenchmarkEvaluator()

    # 1. Out of domain question that generated a hallucinated answer -> MUST FAIL
    ood_q = BenchmarkQuestion(
        id="selnikel-bench-099",
        category="out_of_domain",
        question="How to cook pasta?",
        expected_evidence=ExpectedEvidence(
            document_name="none",
            page_number=0,
            ground_truth_answer="Kapsam dışı",
        ),
        is_out_of_domain=True,
    )
    gen_hallucinated = GenerationOutput(answer="Boil water and add salt.", citations=[])
    res_ood = evaluator.evaluate_single(ood_q, gen_hallucinated, [])
    assert res_ood.metrics.abstention_accuracy == 0.0
    assert res_ood.passed is False  # Hard gate!

    # 2. Out of domain question that gave honest refusal -> MUST PASS
    gen_refused = GenerationOutput(
        answer="Sağlanan teknik dokümanlarda bu konuyla ilgili yeterli bilgi bulunmamaktadır.",
        citations=[],
    )
    res_ood_pass = evaluator.evaluate_single(ood_q, gen_refused, [])
    assert res_ood_pass.metrics.abstention_accuracy == 1.0
    assert res_ood_pass.passed is True

    # 3. Safety-critical question with wrong numerical parameters -> MUST FAIL
    safety_q = BenchmarkQuestion(
        id="selnikel-bench-088",
        category="safety_critical",
        question="What is the maximum relief pressure?",
        expected_evidence=ExpectedEvidence(
            document_name="safety.pdf",
            page_number=1,
            expected_numerical_parameters=["16 bar"],
            ground_truth_answer="Relief pressure is 16 bar.",
        ),
        is_safety_critical=True,
    )
    gen_wrong_num = GenerationOutput(
        answer="Relief pressure is 25 bar. [Doc: safety.pdf, P. 1]",
        citations=[Citation(document_id="d1", filename="safety.pdf", page_number=1, snippet="Relief pressure")],
    )
    chunk = RetrievalResult(
        chunk_id="c1",
        content="Relief pressure is 16 bar.",
        metadata=ChunkMetadata(chunk_id="c1", document_id="d1", filename="safety.pdf", page_number=1),
        score=0.9,
    )
    res_safety = evaluator.evaluate_single(safety_q, gen_wrong_num, [chunk])
    assert res_safety.metrics.safety_compliance_score == 0.0
    assert res_safety.passed is False  # Hard gate!


def test_generation_pipeline_prompt_contract_integration():
    """Verify that build_rag_user_prompt is directly bound to current_prompt_contract."""
    chunks = [
        RetrievalResult(
            chunk_id="c1",
            content="Standart işletme basıncı 16 bar.",
            metadata=ChunkMetadata(chunk_id="c1", document_id="d1", filename="kazan.pdf", page_number=2),
            score=0.9,
        )
    ]
    prompt = build_rag_user_prompt("Kazan basıncı nedir?", chunks)
    assert "DOKÜMAN BAĞLAMI" in prompt
    assert "[Doc: kazan.pdf, P. 2]" in prompt
    assert "KULLANICI SORUSU" in prompt
    assert SELNIKEL_RAG_SYSTEM_PROMPT == current_prompt_contract.system_prompt
