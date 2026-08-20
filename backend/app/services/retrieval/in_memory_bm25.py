import math
import re
from typing import Dict, List, Optional, Tuple
from app.domain.rag import RetrievalFilter, RetrievalResult
from app.domain.document import DomainChunk
from app.services.retrieval.base import BaseRetriever


class InMemoryBM25Index(BaseRetriever):
    """Okapi BM25 in-memory index for offline retrieval benchmarking."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.chunks: List[RetrievalResult] = []
        self.doc_len: List[int] = []
        self.avg_doc_len: float = 0.0
        self.df: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.tf: List[Dict[str, int]] = []
        self.total_docs: int = 0

    @staticmethod
    def tokenize(text: str) -> List[str]:
        """Tokenize text into lowercase alphanumeric tokens, preserving technical units."""
        cleaned = re.sub(r"[^\w\s°/.-]", " ", text.lower())
        return [t.strip() for t in cleaned.split() if t.strip()]

    def index_chunks(self, chunks: List[DomainChunk]) -> None:
        """Indexes a list of DomainChunk objects."""
        self.chunks = []
        self.doc_len = []
        self.tf = []
        self.df = {}
        self.idf = {}
        self.total_docs = len(chunks)

        if not chunks:
            self.avg_doc_len = 0.0
            return

        total_length = 0
        for idx, chunk in enumerate(chunks):
            cid = getattr(chunk, "chunk_id", None) or getattr(chunk.metadata, "chunk_id", f"chunk_{idx}")
            res = RetrievalResult(
                chunk_id=cid,
                content=chunk.content,
                score=0.0,
                metadata=chunk.metadata,
            )
            self.chunks.append(res)

            tokens = self.tokenize(chunk.content)
            length = len(tokens)
            self.doc_len.append(length)
            total_length += length

            term_freq: Dict[str, int] = {}
            for t in tokens:
                term_freq[t] = term_freq.get(t, 0) + 1
            self.tf.append(term_freq)

            for t in term_freq:
                self.df[t] = self.df.get(t, 0) + 1

        self.avg_doc_len = total_length / self.total_docs if self.total_docs > 0 else 0.0

        # Compute IDF: log((N - n + 0.5) / (n + 0.5) + 1)
        for term, doc_freq in self.df.items():
            self.idf[term] = math.log(
                (self.total_docs - doc_freq + 0.5) / (doc_freq + 0.5) + 1.0
            )

    def search(
        self, query: str, top_k: int = 5, document_filter: Optional[str] = None
    ) -> List[RetrievalResult]:
        """Performs BM25 ranked search over indexed chunks."""
        if not self.chunks or not query.strip():
            return []

        query_tokens = self.tokenize(query)
        if not query_tokens:
            return []

        scores: List[Tuple[float, int]] = []

        for idx in range(self.total_docs):
            if document_filter and self.chunks[idx].metadata.filename != document_filter:
                continue

            score = 0.0
            d_len = self.doc_len[idx]
            doc_tf = self.tf[idx]

            for qt in query_tokens:
                if qt not in doc_tf:
                    continue
                f = doc_tf[qt]
                idf = self.idf.get(qt, 0.0)
                numerator = f * (self.k1 + 1.0)
                denominator = f + self.k1 * (1.0 - self.b + self.b * (d_len / self.avg_doc_len))
                score += idf * (numerator / denominator)

            if score > 0.0:
                scores.append((score, idx))

        scores.sort(key=lambda x: x[0], reverse=True)
        top_results = scores[:top_k]

        results: List[RetrievalResult] = []
        for score, idx in top_results:
            orig = self.chunks[idx]
            res = RetrievalResult(
                chunk_id=orig.chunk_id,
                content=orig.content,
                score=round(score, 4),
                metadata=orig.metadata,
            )
            results.append(res)

        return results

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filter_criteria: Optional[RetrievalFilter] = None,
    ) -> List[RetrievalResult]:
        """BaseRetriever async interface implementation."""
        doc_filter = filter_criteria.document_id if filter_criteria else None
        return self.search(query=query, top_k=top_k, document_filter=doc_filter)
