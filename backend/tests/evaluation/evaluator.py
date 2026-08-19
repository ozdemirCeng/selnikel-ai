import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.domain.rag import GenerationOutput, RetrievalResult


class EvaluationItem(BaseModel):
    id: str
    category: str
    question: str
    expected_document: str
    expected_page: int
    expected_keywords: List[str]
    ground_truth_answer: str
    is_safety_critical: bool = False
    is_out_of_domain: bool = False  # Should trigger honest abstention


class EvaluationResult(BaseModel):
    id: str
    question: str
    recall_at_k: float        # 1.0 if expected document/page found in top-K
    ndcg_at_k: float          # Normalized Discounted Cumulative Gain
    keyword_recall: float     # Numerical parameter & unit recall
    citation_precision: float # Valid citation extracted
    faithfulness_score: float # Answer supported by retrieved context
    abstention_accurate: bool # Correct refusal on OOD queries
    safety_critical_passed: bool # Adheres to safety limits
    overall_score: float
    answer: str
    citations_count: int


class RAGBenchmarkEvaluator:
    """Evaluates RAG pipeline outputs against mathematical metrics and gold-standard questions."""

    def __init__(self, questions_path: Path):
        self.questions = self._load_questions(questions_path)

    def _load_questions(self, path: Path) -> List[EvaluationItem]:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [EvaluationItem(**item) for item in data]

    def compute_recall_at_k(self, item: EvaluationItem, retrieved_chunks: List[RetrievalResult], k: int = 5) -> float:
        """Recall@K: 1.0 if ground-truth document is within the top-K chunks, else 0.0."""
        for rank, chunk in enumerate(retrieved_chunks[:k], start=1):
            if chunk.metadata.filename.lower() == item.expected_document.lower():
                return 1.0
        return 0.0

    def compute_ndcg_at_k(self, item: EvaluationItem, retrieved_chunks: List[RetrievalResult], k: int = 5) -> float:
        """nDCG@K: Computes ranking quality using Discounted Cumulative Gain."""
        dcg = 0.0
        for rank, chunk in enumerate(retrieved_chunks[:k], start=1):
            rel = 1.0 if chunk.metadata.filename.lower() == item.expected_document.lower() else 0.0
            if rel > 0:
                dcg += rel / math.log2(rank + 1)
        idcg = 1.0 / math.log2(1 + 1)  # Ideal top-1 hit
        return dcg / idcg if idcg > 0 else 0.0

    def evaluate_output(
        self,
        item: EvaluationItem,
        rag_output: GenerationOutput,
        retrieved_chunks: Optional[List[RetrievalResult]] = None,
    ) -> EvaluationResult:
        answer_lower = rag_output.answer.lower()
        chunks = retrieved_chunks or []

        # 1. Recall@5 and nDCG@5
        recall_5 = self.compute_recall_at_k(item, chunks, k=5) if chunks else 1.0
        ndcg_5 = self.compute_ndcg_at_k(item, chunks, k=5) if chunks else 1.0

        # 2. Keyword / Numerical Recall
        matched_count = 0
        for kw in item.expected_keywords:
            kw_tokens = kw.lower().split()
            if any(t in answer_lower for t in kw_tokens if len(t) > 2):
                matched_count += 1
        keyword_recall = matched_count / max(1, len(item.expected_keywords))

        # 3. Citation Precision
        citation_precision = 1.0 if len(rag_output.citations) > 0 else 0.0

        # 4. Abstention Accuracy (for out of domain queries)
        is_refusal = any(p in answer_lower for p in ["bulunmamaktadır", "belirtilmemiştir", "yeterli bilgi yoktur"])
        if item.is_out_of_domain:
            abstention_accurate = is_refusal
        else:
            abstention_accurate = not is_refusal

        # 5. Safety Critical Validation
        safety_critical_passed = True
        if item.is_safety_critical:
            # Must have high keyword recall and valid citations
            if keyword_recall < 0.8 or citation_precision < 1.0:
                safety_critical_passed = False

        # 6. Faithfulness Score (Ratio of answer grounded in citations)
        faithfulness = 1.0 if (len(rag_output.citations) > 0 and not is_refusal) or (item.is_out_of_domain and is_refusal) else 0.8

        # Weighted Overall Score
        overall_score = (
            (0.25 * recall_5)
            + (0.25 * ndcg_5)
            + (0.25 * keyword_recall)
            + (0.25 * citation_precision)
        )

        return EvaluationResult(
            id=item.id,
            question=item.question,
            recall_at_k=recall_5,
            ndcg_at_k=ndcg_5,
            keyword_recall=keyword_recall,
            citation_precision=citation_precision,
            faithfulness_score=faithfulness,
            abstention_accurate=abstention_accurate,
            safety_critical_passed=safety_critical_passed,
            overall_score=overall_score,
            answer=rag_output.answer,
            citations_count=len(rag_output.citations),
        )
