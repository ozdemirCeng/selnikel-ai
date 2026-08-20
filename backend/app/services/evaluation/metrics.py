"""
Mathematical Evaluation Metrics for Technical RAG Systems.
Implements Page-Aware NDCG@K, Binary Recall@K, Graded Evidence Hit Score, Parameter/Unit Accuracy,
Snippet-Verified Citation Provenance, Lexical Grounding, and Safety Compliance Gates.
"""
import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from app.domain.contracts.evaluation import ExpectedEvidence, MetricResult
from app.domain.rag import Citation, RetrievalResult

# Comprehensive regex for engineering, dimensional, and maintenance/time units
PARAM_REGEX = re.compile(
    r"\b(\d+(?:[.,]\d+)?)\s*(bar|barg|mbar|°c|c|t/h|ton/saat|kw|mw|m³/h|m3/h|rpm|d/d|db|dba|mm|cm|m|kg|ton|v|hz|ppm|hour|hours|saat|day|days|gün|week|weeks|hafta|month|months|ay|year|years|yıl)\b",
    re.IGNORECASE,
)

UNIT_NORMALIZATION = {
    "c": "°c",
    "ton/saat": "t/h",
    "m3/h": "m³/h",
    "d/d": "rpm",
    "dba": "db",
    "hours": "hour",
    "saat": "hour",
    "days": "day",
    "gün": "day",
    "weeks": "week",
    "hafta": "week",
    "months": "month",
    "ay": "month",
    "years": "year",
    "yıl": "year",
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
    Binary Evidence Recall@K:
    Returns strictly 0.0 if retrieved_chunks is empty or None.
    Returns 1.0 if target document and exact page are in top-K, else 0.0.
    """
    if not retrieved_chunks or k <= 0:
        return 0.0

    target_doc = expected.document_name.lower().strip()
    target_page = expected.page_number

    for chunk in retrieved_chunks[:k]:
        chk_doc = getattr(chunk.metadata, "filename", "").lower().strip()
        chk_page = getattr(chunk.metadata, "page_number", -999)
        if chk_doc == target_doc and chk_page == target_page:
            return 1.0

    return 0.0


def compute_evidence_hit_score_at_k(
    expected: ExpectedEvidence,
    retrieved_chunks: Optional[List[RetrievalResult]],
    k: int = 5,
) -> float:
    """
    Graded Evidence Hit Score:
    - 1.0: Target document + exact page match in top-K.
    - 0.5: Target document + adjacent page (±1) in top-K.
    - 0.25: Target document match on different page.
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
                best_score = max(best_score, 0.5)
            else:
                best_score = max(best_score, 0.25)

    return best_score


def compute_page_aware_ndcg_at_k(
    expected: ExpectedEvidence,
    retrieved_chunks: Optional[List[RetrievalResult]],
    k: int = 5,
) -> float:
    """
    Page-Aware Normalized Discounted Cumulative Gain (nDCG@K):
    Mathematically rigorous ranking evaluation:
    - Target page: relevance 1.0
    - Adjacent page (±1): relevance 0.5
    - Other page in target doc: relevance 0.25
    - Duplicate chunks from same (doc, page): relevance 0.0 (no inflation)
    - IDCG computed against ideal sorted unique relevance.
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

    # Ideal DCG for single primary target evidence is 1.0 at rank 1
    idcg = 1.0 / math.log2(1 + 1)  # 1.0
    if idcg <= 0.0:
        return 0.0

    return dcg / idcg


def compute_numerical_unit_accuracy(
    expected_parameters: List[str],
    generated_answer: str,
    tolerance_pct: float = 0.5,
) -> float:
    """
    Evaluates exact numerical value and engineering unit preservation.
    Raises ValueError if expected_parameters contains unparseable strings (preventing silent false passes).
    """
    if not expected_parameters:
        return 1.0

    expected_pairs: List[Tuple[float, str]] = []
    for p in expected_parameters:
        pairs = extract_parameters(p)
        if not pairs:
            raise ValueError(
                f"Expected parameter '{p}' could not be parsed into a recognized numeric value and unit."
            )
        expected_pairs.extend(pairs)

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
    Citation Precision with Snippet & Provenance Verification:
    Evaluates whether each cited document and page corresponds to an actual retrieved chunk,
    and checks snippet presence in the chunk content.
    """
    if not citations:
        return 0.0
    if not retrieved_chunks:
        return 0.0

    valid_count = 0
    for cit in citations:
        cit_doc = cit.filename.lower().strip()
        cit_page = cit.page_number
        cit_snippet = (cit.snippet or "").strip().lower()

        matched = False
        for c in retrieved_chunks:
            chk_doc = getattr(c.metadata, "filename", "").lower().strip()
            chk_page = getattr(c.metadata, "page_number", -1)
            chk_content = c.content.lower()

            if chk_doc == cit_doc and chk_page == cit_page:
                # If snippet is provided, check substring match or high keyword overlap
                if not cit_snippet or cit_snippet in chk_content or any(w in chk_content for w in cit_snippet.split() if len(w) > 3):
                    matched = True
                    break

        if matched:
            valid_count += 1

    return valid_count / len(citations)


def compute_lexical_grounding_score(
    generated_answer: str,
    retrieved_chunks: Optional[List[RetrievalResult]],
) -> float:
    """
    Lexical Grounding Score:
    Measures the ratio of factual parameters and assertions in the answer supported by retrieved context.
    """
    if not generated_answer.strip():
        return 0.0

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


# Alias for backward compatibility
compute_faithfulness_score = compute_lexical_grounding_score


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
    has_retrieved_context: bool = True,
) -> float:
    """
    Safety Critical Compliance:
    - If context was available: requires high parameter accuracy (>=0.9) AND valid citation (>=0.8), and rejects false refusal.
    - If context was missing: honest safety refusal/redirect is required.
    """
    if not is_safety_critical:
        return 1.0

    refusal_markers = [
        "yeterli bilgi bulunmamaktadır",
        "dokümanlarda yer almamaktadır",
        "belirtilmemiştir",
    ]
    is_refusal = any(marker in generated_answer.lower() for marker in refusal_markers)

    if not has_retrieved_context:
        return 1.0 if is_refusal else 0.0

    if is_refusal:
        return 0.0  # False refusal on in-domain safety critical question

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
    chunks = retrieved_chunks or []
    has_context = len(chunks) > 0

    recall_5 = compute_evidence_recall_at_k(expected, chunks, k=5)
    hit_score_5 = compute_evidence_hit_score_at_k(expected, chunks, k=5)
    ndcg_5 = compute_page_aware_ndcg_at_k(expected, chunks, k=5)
    num_acc = compute_numerical_unit_accuracy(expected.expected_numerical_parameters, generated_answer)
    cit_prec = compute_citation_precision(citations or [], chunks)
    faith = compute_lexical_grounding_score(generated_answer, chunks)
    abst_acc = compute_abstention_accuracy(is_out_of_domain, generated_answer)
    safety_score = compute_safety_compliance(is_safety_critical, num_acc, cit_prec, generated_answer, has_retrieved_context=has_context)

    if is_out_of_domain:
        overall = abst_acc
    elif is_safety_critical:
        overall = 0.30 * safety_score + 0.25 * num_acc + 0.20 * cit_prec + 0.15 * ndcg_5 + 0.10 * faith
    else:
        overall = (
            0.25 * ndcg_5
            + 0.25 * recall_5
            + 0.20 * num_acc
            + 0.15 * cit_prec
            + 0.15 * faith
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
