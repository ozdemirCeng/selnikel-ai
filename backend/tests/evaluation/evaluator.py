import json
from pathlib import Path
from typing import Any, Dict, List
from pydantic import BaseModel
from app.domain.rag import GenerationOutput


class EvaluationItem(BaseModel):
    id: str
    category: str
    question: str
    expected_document: str
    expected_page: int
    expected_keywords: List[str]
    ground_truth_answer: str


class EvaluationResult(BaseModel):
    id: str
    question: str
    context_relevance: float  # 0.0 to 1.0 (retrieved expected doc/page)
    keyword_recall: float     # 0.0 to 1.0 (contained required engineering units/terms)
    citation_precision: float # 0.0 to 1.0 (valid citations produced)
    overall_score: float
    answer: str
    citations_count: int


class RAGBenchmarkEvaluator:
    """Evaluates RAG pipeline outputs against gold-standard engineering questions."""

    def __init__(self, questions_path: Path):
        self.questions = self._load_questions(questions_path)

    def _load_questions(self, path: Path) -> List[EvaluationItem]:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [EvaluationItem(**item) for item in data]

    def evaluate_output(
        self,
        item: EvaluationItem,
        rag_output: GenerationOutput,
    ) -> EvaluationResult:
        answer_lower = rag_output.answer.lower()

        # 1. Keyword / Parameter Recall (Checks key numerical values and concepts)
        matched_count = 0
        for kw in item.expected_keywords:
            kw_tokens = kw.lower().split()
            # If any significant token or the phrase is in the answer
            if any(t in answer_lower for t in kw_tokens if len(t) > 2):
                matched_count += 1

        keyword_recall = matched_count / max(1, len(item.expected_keywords))

        # 2. Context Relevance & Citation Precision
        has_expected_doc = any(
            c.filename.lower() == item.expected_document.lower()
            for c in rag_output.citations
        ) or any(
            item.expected_document.lower() in src.lower()
            for src in rag_output.sources_used
        )

        context_relevance = 1.0 if has_expected_doc else 0.5

        # 3. Citation Precision
        citation_precision = 1.0 if len(rag_output.citations) > 0 else 0.0

        # Weighted Overall Score (40% Keywords, 30% Context Relevance, 30% Citation Precision)
        overall_score = (
            (0.40 * keyword_recall)
            + (0.30 * context_relevance)
            + (0.30 * citation_precision)
        )

        return EvaluationResult(
            id=item.id,
            question=item.question,
            context_relevance=context_relevance,
            keyword_recall=keyword_recall,
            citation_precision=citation_precision,
            overall_score=overall_score,
            answer=rag_output.answer,
            citations_count=len(rag_output.citations),
        )
