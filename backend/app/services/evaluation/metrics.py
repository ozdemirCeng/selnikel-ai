"""
Mathematical Evaluation Metrics for Technical RAG Systems.
Implements Page-Aware NDCG@K, Exact Parameter/Unit Recall, Citation Provenance, Faithfulness, and Safety Auditing.
"""
import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from app.domain.contracts.evaluation import ExpectedEvidence, MetricResult
from app.domain.rag import Citation, RetrievalResult

# Regex matching numbers with optional decimal point/comma followed by engineering units
PARAM_REGEX = re.compile(
    r"\b(\d+(?:[.,]\d+)?)\s*(bar|barg|mbar|°c|c|t/h|ton/saat|kw|mw|m³/h|m3/h|rpm|d/d|db|dba|mm|kg|v|hz|ppm)\b",
    re.IGNORECASE,
)

UNIT_NORMALIZATION = {
    "c": "°c",
    "ton/saat": "t/h",
    "m3/h": "m³/h",
    "d/d": "rpm",
    "dba": "db",
}


def normalize_unit(unit_str: str) -> str:
    """Normalize colloquial engineering unit variations to standard canonical forms."""
    u = unit_str.lower().strip()
    return UNIT_NORMALIZATION.get(u, u)


def extract_parameters(text: str) -> List[Tuple[float, str]]:
    """Extract (numeric_value, canonical_unit) tuples from text with comma normalization."""
    matches = PARAM_REGEX.findall(text)
    params = []
    for raw_val, raw_unit in matches:
        val = float(raw_val.replace(",", "."))
        unit = normalize_unit(raw_unit)
        params.append((val, unit))
    return params


def compute_evidence_recall_at_k(
    expected: ExpectedEvidence,
    retrieved_chunks: Optional[List[RetrievalResult]],
    k: int = 5,
) -> float:
    """
    Evidence Recall@K:
    Returns 0.0 strictly if retrieved_chunks is empty or None.
    - 1.0: Target document + exact page match in top-K.
    - 0.75: Target document + adjacent page (±1) in top-K.
    - 0.5: Target document match in top-K.
    - 0.0: Target document not retrieved in top-K.
    """
    if not retrieved_chunks or k <= 0:
        return 0.0

    target_doc = expected.document_name.lower().strip()
    target_page = expected.page_number

    best_score = 0.0
    for chunk in retrieved_chunks[:k]:
        chk_doc = getattr(chunk.metadata, "filename", "").lower().strip()
        chk_page = getattr(chunk.metadata, "page_number", -999)

        if chk_doc == target_doc:
            if chk_page == target_page:
                return 1.0
            elif abs(chk_page - target_page) <= 1:
                best_score = max(best_score, 0.75)
            else:
                best_score = max(best_score, 0.5)

    return best_score


def compute_page_aware_ndcg_at_k(
    expected: ExpectedEvidence,
    retrieved_chunks: Optional[List[RetrievalResult]],
    k: int = 5,
) -> float:
    """
    Page-Aware Normalized Discounted Cumulative Gain (nDCG@K):
    Returns 0.0 strictly if retrieved_chunks is empty or None.
    Disallows duplicate gain inflation from repeated chunks of the same page.
    """
    if not retrieved_chunks or k <= 0:
        return 0.0

    target_doc = expected.document_name.lower().strip()
    target_page = expected.page_number

    seen_pages: Set[Tuple[str, int]] = set()
    dcg = 0.0

    for rank, chunk in enumerate(retrieved_chunks[:k], start=1):
        chk_doc = getattr(chunk.metadata, "filename", "").lower().strip()
        chk_page = getattr(chunk.metadata, "page_number", -999)

        page_key = (chk_doc, chk_page)
        if page_key in seen_pages:
            # Duplicate chunk from already rewarded page yields zero incremental gain
            relevance = 0.0
        else:
            seen_pages.add(page_key)
            if chk_doc == target_doc:
                if chk_page == target_page:
                    relevance = 1.0
                elif abs(chk_page - target_page) <= 1:
                    relevance = 0.5
                else:
                    relevance = 0.25
            else:
                relevance = 0.0

        if relevance > 0.0:
            dcg += relevance / math.log2(rank + 1)

    idcg = 1.0 / math.log2(1 + 1)  # Ideal top-1 hit with relevance 1.0
    return min(1.0, dcg / idcg)


def compute_numerical_unit_accuracy(
    expected_parameters: List[str],
    generated_answer: str,
    tolerance_pct: float = 0.5,
) -> float:
    """
    Evaluates exact numerical value and engineering unit preservation.
    Matches extracted (value, unit) pairs within tolerance_pct.
    """
    if not expected_parameters:
        return 1.0

    expected_pairs: List[Tuple[float, str]] = []
    for p in expected_parameters:
        pairs = extract_parameters(p)
        expected_pairs.extend(pairs)

    if not expected_pairs:
        return 1.0

    answer_pairs = extract_parameters(generated_answer)
    if not answer_pairs:
        return 0.0

    matched_count = 0
    for exp_val, exp_unit in expected_pairs:
        matched = False
        for ans_val, ans_unit in answer_pairs:
            if ans_unit == exp_unit:
                if abs(exp_val - ans_val) <= (abs(exp_val) * (tolerance_pct / 100.0) + 1e-6):
                    matched = True
                    break
        if matched:
            matched_count += 1

    return matched_count / len(expected_pairs)


def compute_citation_precision(
    citations: Optional[List[Citation]],
    retrieved_chunks: Optional[List[RetrievalResult]],
) -> float:
    """
    Citation Precision:
    Evaluates whether each cited document and page corresponds to an actual chunk in the retrieved context.
    """
    if not citations:
        return 0.0
    if not retrieved_chunks:
        return 0.0

    retrieved_provenance = {
        (
            getattr(c.metadata, "filename", "").lower().strip(),
            getattr(c.metadata, "page_number", -1),
        )
        for c in retrieved_chunks
    }

    valid_count = 0
    for cit in citations:
        cit_doc = cit.filename.lower().strip()
        cit_page = cit.page_number
        if (cit_doc, cit_page) in retrieved_provenance:
            valid_count += 1
        elif any(doc == cit_doc for doc, _ in retrieved_provenance):
            valid_count += 0.5

    return valid_count / len(citations)


def compute_faithfulness_score(
    generated_answer: str,
    retrieved_chunks: Optional[List[RetrievalResult]],
) -> float:
    """
    Faithfulness Score:
    Measures the ratio of factual parameters and assertions in the answer supported by retrieved context.
    """
    if not generated_answer.strip():
        return 0.0

    # If answer is an explicit honest abstention, faithfulness is 1.0
    refusal_markers = [
        "yeterli bilgi bulunmamaktadır",
        "dokümanlarda yer almamaktadır",
        "belirtilmemiştir",
        "kapsam dışı",
        "bulunamadı",
    ]
    if any(marker in generated_answer.lower() for marker in refusal_markers):
        return 1.0

    if not retrieved_chunks:
        return 0.0

    context_text = " ".join(c.content for c in retrieved_chunks)
    context_params = extract_parameters(context_text)
    answer_params = extract_parameters(generated_answer)

    if not answer_params:
        # Textual keyword overlap
        words = [w.lower() for w in re.findall(r"\b\w{4,}\b", generated_answer)]
        if not words:
            return 1.0
        supported_words = sum(1 for w in words if w in context_text.lower())
        return min(1.0, supported_words / len(words))

    supported_params = 0
    for a_val, a_unit in answer_params:
        if any(c_unit == a_unit and abs(c_val - a_val) < 1e-4 for c_val, c_unit in context_params):
            supported_params += 1

    return supported_params / len(answer_params)


def compute_abstention_accuracy(
    is_out_of_domain: bool,
    generated_answer: str,
) -> float:
    """
    Abstention Accuracy:
    Verifies that out-of-domain questions trigger honest refusal, and in-domain questions do not false-refuse.
    """
    refusal_markers = [
        "yeterli bilgi bulunmamaktadır",
        "dokümanlarda yer almamaktadır",
        "belirtilmemiştir",
        "kapsam dışı",
        "bulunamadı",
    ]
    is_refusal = any(marker in generated_answer.lower() for marker in refusal_markers)

    if is_out_of_domain:
        return 1.0 if is_refusal else 0.0
    else:
        return 0.0 if is_refusal else 1.0


def compute_safety_compliance(
    is_safety_critical: bool,
    numerical_accuracy: float,
    citation_precision: float,
    generated_answer: str,
) -> float:
    """
    Safety Critical Compliance:
    Enforces strict threshold (numerical >= 0.9 and citation >= 0.8) on safety-critical parameters.
    """
    if not is_safety_critical:
        return 1.0

    refusal_markers = [
        "yeterli bilgi bulunmamaktadır",
        "dokümanlarda yer almamaktadır",
        "belirtilmemiştir",
    ]
    if any(marker in generated_answer.lower() for marker in refusal_markers):
        return 1.0  # Honest safety abstention is 100% compliant

    if numerical_accuracy >= 0.9 and citation_precision >= 0.8:
        return 1.0
    return 0.0


def evaluate_metrics(
    expected: ExpectedEvidence,
    retrieved_chunks: Optional[List[RetrievalResult]],
    generated_answer: str,
    citations: Optional[List[Citation]] = None,
    is_safety_critical: bool = False,
    is_out_of_domain: bool = False,
) -> MetricResult:
    """Compute complete composite metric result for a single question evaluation."""
    recall_5 = compute_evidence_recall_at_k(expected, retrieved_chunks, k=5)
    ndcg_5 = compute_page_aware_ndcg_at_k(expected, retrieved_chunks, k=5)
    num_acc = compute_numerical_unit_accuracy(expected.expected_numerical_parameters, generated_answer)
    cit_prec = compute_citation_precision(citations or [], retrieved_chunks)
    faith = compute_faithfulness_score(generated_answer, retrieved_chunks)
    abst_acc = compute_abstention_accuracy(is_out_of_domain, generated_answer)
    safety_score = compute_safety_compliance(is_safety_critical, num_acc, cit_prec, generated_answer)

    overall = (
        0.20 * recall_5
        + 0.20 * ndcg_5
        + 0.20 * num_acc
        + 0.15 * cit_prec
        + 0.15 * faith
        + 0.10 * safety_score
    )

    return MetricResult(
        recall_at_5=round(recall_5, 4),
        ndcg_at_5=round(ndcg_5, 4),
        numerical_unit_accuracy=round(num_acc, 4),
        citation_precision=round(cit_prec, 4),
        faithfulness_score=round(faith, 4),
        abstention_accuracy=round(abst_acc, 4),
        safety_compliance_score=round(safety_score, 4),
        overall_score=round(overall, 4),
    )
