from typing import Dict, List, Optional
from app.core.logging import logger
from app.domain.rag import RetrievalFilter, RetrievalResult
from app.infrastructure.qdrant import QdrantVectorRepository, qdrant_repo
from app.services.embedding.base import BaseEmbeddingProvider
from app.services.embedding.factory import embedding_provider
from app.services.retrieval.base import BaseRetriever


class QdrantHybridRetriever(BaseRetriever):
    """Hybrid Retriever combining dense semantic search and sparse keyword matching
    via Reciprocal Rank Fusion (RRF) with metadata pre-filtering.
    """

    def __init__(
        self,
        embed_provider: BaseEmbeddingProvider = embedding_provider,
        vector_repo: QdrantVectorRepository = qdrant_repo,
        rrf_k: int = 60,
    ):
        self.embedding_provider = embed_provider
        self.vector_repo = vector_repo
        self.rrf_k = rrf_k

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filter_criteria: Optional[RetrievalFilter] = None,
    ) -> List[RetrievalResult]:
        """Perform hybrid retrieval using dense vectors and Reciprocal Rank Fusion."""
        if not query.strip():
            return []

        # 1. Compute Dense Query Embedding
        dense_vector = await self.embedding_provider.embed_query(query)

        # 2. Search Dense Vectors in Qdrant (fetch 2x top_k candidates for fusion)
        fetch_k = max(10, top_k * 2)
        dense_results = await self.vector_repo.search(
            query_vector=dense_vector,
            top_k=fetch_k,
            filter_criteria=filter_criteria,
        )

        # 3. If dense results found, apply Lexical / Exact Term Re-ranking Boost
        fused_results = self._apply_hybrid_rrf_scoring(
            query=query,
            candidates=dense_results,
            top_k=top_k,
        )

        logger.info(
            f"Hybrid retrieval for query '{query[:30]}...' yielded {len(fused_results)} chunks (top_k={top_k})."
        )
        return fused_results

    def _apply_hybrid_rrf_scoring(
        self,
        query: str,
        candidates: List[RetrievalResult],
        top_k: int,
    ) -> List[RetrievalResult]:
        """Combine dense rank with exact keyword match scoring using RRF."""
        if not candidates:
            return []

        query_terms = set(query.lower().split())
        scored_candidates: List[RetrievalResult] = []

        for dense_rank, item in enumerate(candidates, start=1):
            content_lower = item.content.lower()

            # Calculate keyword match density
            matched_terms = [t for t in query_terms if t in content_lower and len(t) > 2]
            keyword_score = len(matched_terms) / max(1, len(query_terms))

            # RRF Combination: 1 / (k + dense_rank) + keyword_boost
            dense_rrf = 1.0 / (self.rrf_k + dense_rank)
            keyword_rrf = keyword_score * (1.0 / (self.rrf_k + 1))

            combined_score = (0.7 * dense_rrf) + (0.3 * keyword_rrf)
            
            scored_candidates.append(
                RetrievalResult(
                    chunk_id=item.chunk_id,
                    content=item.content,
                    metadata=item.metadata,
                    score=combined_score,
                )
            )

        # Sort by combined score descending
        scored_candidates.sort(key=lambda x: x.score, reverse=True)
        return scored_candidates[:top_k]


# Default singleton instance
hybrid_retriever = QdrantHybridRetriever()
