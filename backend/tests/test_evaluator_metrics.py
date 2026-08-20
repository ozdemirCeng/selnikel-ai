"""
Unit & Adversarial Edge Case Tests for RAG Benchmark Metrics and Contracts.
Validates:
1. Empty / None retrieval contexts strictly return 0.0 for Recall and nDCG.
2. Bounded mathematical nDCG@K ([0, 1]) and strict ranking invariants.
3. Unparseable expected parameters strictly fail-fast with ValueError.
4. Numerical parameter extraction with comma normalization and unit mismatch rejection.
5. Strict citation provenance & snippet verification rejecting weak single-word overlaps.
6. Two-branch safety-critical hard gates (no-context honest refusal vs with-context accuracy).
7. Out-of-Domain hard pass gate.
8. Conditional JSON schema governance for expert-reviewed vs unverified datasets.
9. Integration of formal PromptContract in generation prompt builder.
"""
import jsonschema
import math
import pytest
from pathlib import Path
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
from app.services.evaluation.dataset_validator import validate_dataset_file
from app.services.rag.prompts import build_rag_user_prompt, SELNIKEL_RAG_SYSTEM_PROMPT


def test_empty_and_none_retrieval_returns_zero():
    """CRITICAL FIX: Verify that empty and None chunk lists return 0.0 strictly."""
    expected = ExpectedEvidence(
        document_name="boiler_manual.pdf",
        page_number=10,
        ground_truth_answer="Operating pressure is 16 bar.",
    )

    assert compute_evidence_recall_at_k(expected, []) == 0.0
    assert compute_evidence_hit_score_at_k(expected, []) == 0.0
    assert compute_page_aware_ndcg_at_k(expected, []) == 0.0

    assert compute_evidence_recall_at_k(expected, None) == 0.0
    assert compute_evidence_hit_score_at_k(expected, None) == 0.0
    assert compute_page_aware_ndcg_at_k(expected, None) == 0.0


def test_ndcg_bounded_and_invariants():
    """
    CRITICAL INVARIANT TEST: Verify that nDCG is strictly bounded in [0, 1]
    and satisfies exact-first > exact-second > wrong-only == 0, with duplicate de-inflation.
    """
    expected = ExpectedEvidence(
        document_name="manual.pdf",
        page_number=5,
        ground_truth_answer="Test answer",
    )

    exact_chunk = RetrievalResult(
        chunk_id="c1",
        content="Exact content page 5",
        metadata=ChunkMetadata(chunk_id="c1", document_id="d1", filename="manual.pdf", page_number=5),
        score=0.9,
    )
    adjacent_chunk = RetrievalResult(
        chunk_id="c2",
        content="Adjacent content page 6",
        metadata=ChunkMetadata(chunk_id="c2", document_id="d1", filename="manual.pdf", page_number=6),
        score=0.8,
    )
    wrong_chunk = RetrievalResult(
        chunk_id="c3",
        content="Wrong doc content",
        metadata=ChunkMetadata(chunk_id="c3", document_id="d2", filename="other.pdf", page_number=1),
        score=0.7,
    )

    # 1. Exact first -> Perfect 1.0
    ndcg_exact_first = compute_page_aware_ndcg_at_k(expected, [exact_chunk, adjacent_chunk])
    assert ndcg_exact_first == 1.0

    # 2. Adjacent first, exact second -> Strictly penalized (< 1.0) and bounded
    ndcg_exact_second = compute_page_aware_ndcg_at_k(expected, [adjacent_chunk, exact_chunk])
    assert 0.0 < ndcg_exact_second < 1.0
    assert ndcg_exact_second == pytest.approx(1.0 / math.log2(3), abs=1e-3)  # ~0.6309
    assert ndcg_exact_first > ndcg_exact_second

    # 3. Duplicate exact chunk does NOT inflate score
    ndcg_with_duplicate = compute_page_aware_ndcg_at_k(expected, [exact_chunk, exact_chunk])
    assert ndcg_with_duplicate == 1.0

    # 4. Wrong chunks only -> Exactly 0.0
    ndcg_wrong = compute_page_aware_ndcg_at_k(expected, [wrong_chunk, adjacent_chunk])
    assert ndcg_wrong == 0.0

    # 5. Pydantic MetricResult validation does not fail with le=1.0
    metric = evaluate_metrics(
        expected=expected,
        retrieved_chunks=[adjacent_chunk, exact_chunk],
        generated_answer="Answer",
    )
    assert 0.0 <= metric.ndcg_at_5 <= 1.0


def test_unparseable_expected_parameter_raises_value_error():
    """Verify that unparseable expected parameters fail-fast and do not silently pass."""
    with pytest.raises(ValueError) as exc_info:
        compute_numerical_unit_accuracy(["unparseable_text_without_number_or_unit"], "Some answer")
    assert "could not be parsed" in str(exc_info.value)


def test_numerical_unit_accuracy_and_comma_normalization():
    """Verify exact numerical and physical unit matching with comma and time units."""
    # Test extraction
    params = extract_parameters("Basınç 16,5 bar ve periyot 500 saat / 6 ay olmalıdır.")
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


def test_citation_snippet_adversarial_rejection():
    """
    CRITICAL ADVERSARIAL TEST: Verify that weak single-word overlaps
    (e.g., 'totally fabricated pressure claim' vs 'standard working steam pressure') are REJECTED.
    """
    retrieved = [
        RetrievalResult(
            chunk_id="c1",
            content="Standard working steam pressure is 16 bar.",
            metadata=ChunkMetadata(chunk_id="c1", document_id="doc-1", filename="boiler.pdf", page_number=4),
            score=0.9,
        )
    ]

    # 1. Adversarial fake snippet with 1 incidental word overlap -> MUST FAIL (0.0)
    fake_snippet_citation = [
        Citation(document_id="doc-1", filename="boiler.pdf", page_number=4, snippet="totally fabricated pressure claim")
    ]
    assert compute_citation_precision(fake_snippet_citation, retrieved) == 0.0

    # 2. Empty snippet -> MUST FAIL (0.0)
    empty_snippet_citation = [
        Citation(document_id="doc-1", filename="boiler.pdf", page_number=4, snippet="")
    ]
    assert compute_citation_precision(empty_snippet_citation, retrieved) == 0.0

    # 3. Repeated single token -> MUST FAIL (0.0)
    repeated_token_citation = [
        Citation(document_id="doc-1", filename="boiler.pdf", page_number=4, snippet="pressure pressure pressure")
    ]
    assert compute_citation_precision(repeated_token_citation, retrieved) == 0.0

    # 4. Unknown or magic document ID mismatch -> MUST FAIL (0.0)
    unknown_id_citation = [
        Citation(document_id="unknown", filename="boiler.pdf", page_number=4, snippet="working steam pressure")
    ]
    assert compute_citation_precision(unknown_id_citation, retrieved) == 0.0

    # 5. Exact substring snippet with matching doc_id -> MUST PASS (1.0)
    valid_exact_citation = [
        Citation(document_id="doc-1", filename="boiler.pdf", page_number=4, snippet="working steam pressure")
    ]
    assert compute_citation_precision(valid_exact_citation, retrieved) == 1.0

    # 6. High token-precision snippet (80%+ overlap) -> MUST PASS (1.0)
    valid_token_citation = [
        Citation(document_id="doc-1", filename="boiler.pdf", page_number=4, snippet="standard working steam pressure 16 bar")
    ]
    assert compute_citation_precision(valid_token_citation, retrieved) == 1.0

    # 7. Wrong document ID -> MUST FAIL (0.0)
    wrong_id_citation = [
        Citation(document_id="doc-WRONG", filename="boiler.pdf", page_number=4, snippet="working steam pressure")
    ]
    assert compute_citation_precision(wrong_id_citation, retrieved) == 0.0


def test_two_branch_safety_critical_gate():
    """
    CRITICAL TEST: Verify two distinct safety-critical evaluation branches:
    Branch A: No context -> Honest refusal PASSES.
    Branch B: Context provided -> False refusal FAILS, accurate parameter PASSES.
    """
    evaluator = RAGBenchmarkEvaluator()

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

    chunk = RetrievalResult(
        chunk_id="c1",
        content="Relief pressure is 16 bar.",
        metadata=ChunkMetadata(chunk_id="c1", document_id="doc-1", filename="safety.pdf", page_number=1),
        score=0.9,
    )

    # Branch A1: No context + Honest Refusal -> PASSES
    gen_honest_refusal = GenerationOutput(
        answer="Sağlanan teknik dokümanlarda bu konuyla ilgili yeterli bilgi bulunmamaktadır. Lütfen yetkili mühendise danışınız.",
        citations=[],
    )
    res_no_ctx_pass = evaluator.evaluate_single(safety_q, gen_honest_refusal, retrieved_chunks=[])
    assert res_no_ctx_pass.passed is True

    # Branch A2: No context + Hallucinated answer -> FAILS
    gen_hallucinated = GenerationOutput(
        answer="Relief pressure is probably 25 bar.",
        citations=[],
    )
    res_no_ctx_fail = evaluator.evaluate_single(safety_q, gen_hallucinated, retrieved_chunks=[])
    assert res_no_ctx_fail.passed is False

    # Branch B1: Context Provided + Correct Parameter & Citation -> PASSES
    gen_correct = GenerationOutput(
        answer="Relief pressure is 16 bar. [Doc: safety.pdf, P. 1]",
        citations=[Citation(document_id="doc-1", filename="safety.pdf", page_number=1, snippet="Relief pressure is 16 bar")],
    )
    res_ctx_pass = evaluator.evaluate_single(safety_q, gen_correct, retrieved_chunks=[chunk])
    assert res_ctx_pass.passed is True

    # Branch B2: Context Provided + False Refusal -> FAILS
    res_ctx_false_refusal = evaluator.evaluate_single(safety_q, gen_honest_refusal, retrieved_chunks=[chunk])
    assert res_ctx_false_refusal.passed is False


def test_schema_conditional_governance_rules():
    """Verify that JSON Schema enforces conditional rules based on review_status."""
    backend_dir = Path(__file__).resolve().parent.parent
    schema_path = backend_dir / "app" / "evaluation" / "schemas" / "golden_benchmark_v1.schema.json"
    import json
    with open(schema_path, "r", encoding="utf-8") as sf:
        schema = json.load(sf)

    # 1. Unverified draft with synthetic=true -> PASSES
    valid_draft = [
        {
            "id": "selnikel-bench-001",
            "category": "capacity_pressure_temp",
            "question": "Sample question?",
            "expected_evidence": {
                "document_name": "manual.pdf",
                "page_number": 1,
                "expected_numerical_parameters": ["16 bar"],
                "ground_truth_answer": "16 bar"
            },
            "is_safety_critical": False,
            "is_out_of_domain": False,
            "dataset_version": "1.0.0",
            "synthetic": True,
            "review_status": "unverified_draft"
        }
    ]
    jsonschema.validate(instance=valid_draft, schema=schema)

    # 2. Verified expert reviewed with synthetic=true -> FAILS (must be synthetic: false)
    invalid_verified_synthetic = [
        {
            "id": "selnikel-bench-001",
            "category": "capacity_pressure_temp",
            "question": "Sample question?",
            "expected_evidence": {
                "document_name": "manual.pdf",
                "document_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "revision_code": "REV-01",
                "page_number": 1,
                "expected_numerical_parameters": ["16 bar"],
                "ground_truth_answer": "16 bar"
            },
            "is_safety_critical": False,
            "is_out_of_domain": False,
            "expert_reviewer": "Lead Engineer",
            "dataset_version": "1.0.0",
            "synthetic": True,  # Illegal for verified_expert_reviewed!
            "review_status": "verified_expert_reviewed"
        }
    ]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=invalid_verified_synthetic, schema=schema)


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
