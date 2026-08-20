"""
Mathematical Evaluation Metrics for Technical RAG Systems.
Implements Bounded Page-Aware NDCG@K, Binary Recall@K, Graded Evidence Hit Score, Parameter/Unit Accuracy,
Strict Provenance & Snippet-Verified Citation Precision, Lexical Grounding, and Two-Branch Safety Compliance Gates.
"""
import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from app.domain.contracts.evaluation import ExpectedEvidence, MetricResult
from app.domain.rag import Citation, RetrievalResult

# Comprehensive regex for engineering, dimensional, and maintenance/time units
PARAM_REGEX = re.compile(
    r"\b(\d+(?:[.,]\d+)?)\s*(bar|barg|mbar|°c|c|t/h|ton/saat|kw|mw|kwh|m³/h|m3/h|rpm|d/d|db|dba|mm|cm|m|kg|kg/h|ton|v|hz|ppm|nm|micron|microns|µm|mg/nm³|mg/kwh|hour|hours|saat|day|days|gün|week|weeks|hafta|month|months|ay|year|years|yıl)\b",
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
    "microns": "micron",
    "µm": "micron",
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
    - Target exact page: relevance 1.0 (only the first instance in top-K gets gain).
    - Duplicate chunks of target page: relevance 0.0 (no inflation).
    - All non-target pages: relevance 0.0.
    - IDCG = 1.0 / log2(2) = 1.0 (ideal rank 1 hit).
    - Invariants: 0.0 <= nDCG <= 1.0; exact-first (1.0) > exact-second (~0.6309); wrong-only = 0.0.
    """
    if not retrieved_chunks or k <= 0:
        return 0.0

    target_doc = expected.document_name.lower().strip()
    target_page = expected.page_number

    seen_target = False
    dcg = 0.0

    for rank, chunk in enumerate(retrieved_chunks[:k], start=1):
        chk_doc = getattr(chunk.metadata, "filename", "").lower().strip()
        chk_page = getattr(chunk.metadata, "page_number", -999)

        if chk_doc == target_doc and chk_page == target_page:
            if not seen_target:
                seen_target = True
                dcg = 1.0 / math.log2(rank + 1)
                break

    # IDCG for single primary target evidence is 1.0 / log2(2) = 1.0
    idcg = 1.0 / math.log2(1 + 1)  # 1.0
    return round(dcg / idcg, 4)


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

    return round(matched_count / len(expected_pairs), 4)


def _normalize_text_for_matching(text: str) -> str:
    """Normalize text by lowercasing, stripping punctuation, and collapsing whitespace."""
    text = re.sub(r"[^\w\s]", " ", text.lower())
    return " ".join(text.split())


def compute_citation_precision(
    citations: Optional[List[Citation]],
    retrieved_chunks: Optional[List[RetrievalResult]],
) -> float:
    """
    Citation Precision with Strict Provenance & Snippet Verification:
    - Zero bypass on document_id: exact match required (cit.document_id == chunk.metadata.document_id).
    - Non-empty snippet required: empty or whitespace-only snippet strictly fails (0.0).
    - Snippet matching:
      1. Exact normalized substring in chunk content (with >= 10 chars and >= 2 unique tokens), OR
      2. Unique token precision >= 0.80 over at least 3 distinct meaningful tokens (>2 chars).
      Repeated single tokens (e.g. 'pressure pressure pressure') strictly fail.
    """
    if not citations or not retrieved_chunks:
        return 0.0

    valid_count = 0
    for cit in citations:
        cit_doc = cit.filename.lower().strip()
        cit_page = cit.page_number
        cit_id = (cit.document_id or "").strip()
        cit_snippet = (cit.snippet or "").strip()

        # Rule 1: Non-empty snippet is strictly required
        if not cit_snippet or len(cit_snippet) < 5:
            continue

        norm_snip = _normalize_text_for_matching(cit_snippet)
        unique_snip_tokens = set(t for t in norm_snip.split() if len(t) > 2)

        # Rule 2: Minimum token uniqueness (reject repeated single words)
        if len(unique_snip_tokens) < 2:
            continue

        matched = False
        for c in retrieved_chunks:
            chk_doc = getattr(c.metadata, "filename", "").lower().strip()
            chk_page = getattr(c.metadata, "page_number", -1)
            chk_id = getattr(c.metadata, "document_id", "").strip()
            chk_content = c.content

            # Strict Provenance match: filename, page, and exact document_id match
            doc_matches = (chk_doc == cit_doc)
            page_matches = (chk_page == cit_page)
            id_matches = (chk_id == cit_id)

            if doc_matches and page_matches and id_matches:
                norm_chunk = _normalize_text_for_matching(chk_content)
                chunk_token_set = set(norm_chunk.split())

                # Exact normalized substring match
                if norm_snip in norm_chunk and len(norm_snip) >= 10:
                    matched = True
                    break

                # Distinct token-level precision >= 0.80 with at least 3 distinct tokens
                if len(unique_snip_tokens) >= 3:
                    overlap_count = len(unique_snip_tokens & chunk_token_set)
                    token_precision = overlap_count / len(unique_snip_tokens)
                    if token_precision >= 0.80:
                        matched = True
                        break

        if matched:
            valid_count += 1

    return round(valid_count / len(citations), 4)


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
        return min(1.0, round(supported_words / len(words), 4))

    supported_params = 0
    for a_val, a_unit in answer_params:
        if any(c_unit == a_unit and abs(c_val - a_val) < 1e-4 for c_val, c_unit in context_params):
            supported_params += 1

    return round(supported_params / len(answer_params), 4)


# Alias for backward compatibility
compute_faithfulness_score = compute_lexical_grounding_score


def compute_abstention_accuracy(
    is_out_of_domain: bool,
    generated_answer: str,
    has_retrieved_context: bool = True,
) -> float:
    """
    Abstention Accuracy:
    - If out-of-domain OR no context available: honest refusal -> 1.0, hallucinated answer -> 0.0.
    - If in-domain AND context available: response -> 1.0, false refusal -> 0.0.
    """
    refusal_markers = [
        "yeterli bilgi bulunmamaktadır",
        "dokümanlarda yer almamaktadır",
        "belirtilmemiştir",
        "kapsam dışı",
        "kapsamı dışı",
        "kapsamı dışındadır",
        "kapsam dışındadır",
        "bulunamadı",
        "cevap veremiyorum",
        "bilgi bulunamadı",
        "yer almıyor",
    ]
    is_refusal = any(marker in generated_answer.lower() for marker in refusal_markers)

    if is_out_of_domain or not has_retrieved_context:
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
    - If context was missing: honest safety refusal/redirect is required (1.0).
    """
    if not is_safety_critical:
        return 1.0

    refusal_markers = [
        "yeterli bilgi bulunmamaktadır",
        "dokümanlarda yer almamaktadır",
        "belirtilmemiştir",
        "kapsam dışı",
        "kapsamı dışı",
        "kapsamı dışındadır",
        "kapsam dışındadır",
        "bulunamadı",
        "cevap veremiyorum",
        "bilgi bulunamadı",
        "yer almıyor",
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
    expected: Optional[ExpectedEvidence],
    retrieved_chunks: Optional[List[RetrievalResult]],
    generated_answer: str,
    citations: Optional[List[Citation]] = None,
    is_safety_critical: bool = False,
    is_out_of_domain: bool = False,
) -> MetricResult:
    """Compute complete composite metric result for a single question evaluation."""
    chunks = retrieved_chunks or []
    has_context = len(chunks) > 0

    if is_out_of_domain or expected is None:
        recall_5 = 0.0
        ndcg_5 = 0.0
        num_acc = 1.0
        cit_prec = 1.0
        faith = 1.0
        abst_acc = compute_abstention_accuracy(True, generated_answer, has_retrieved_context=has_context)
        safety_score = 1.0
        overall = abst_acc
    else:
        recall_5 = compute_evidence_recall_at_k(expected, chunks, k=5)
        ndcg_5 = compute_page_aware_ndcg_at_k(expected, chunks, k=5)
        num_acc = compute_numerical_unit_accuracy(expected.expected_numerical_parameters, generated_answer)
        cit_prec = compute_citation_precision(citations or [], chunks)
        faith = compute_lexical_grounding_score(generated_answer, chunks)
        abst_acc = compute_abstention_accuracy(is_out_of_domain, generated_answer, has_retrieved_context=has_context)
        safety_score = compute_safety_compliance(is_safety_critical, num_acc, cit_prec, generated_answer, has_retrieved_context=has_context)

        if is_safety_critical:
            if not has_context:
                overall = safety_score
            else:
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
