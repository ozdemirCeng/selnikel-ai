from abc import ABC, abstractmethod
from typing import List, Optional
from app.core.config import settings
from app.core.logging import logger
from app.domain.rag import RetrievalResult


class BaseReranker(ABC):
    """Abstract interface for Cross-Encoder rerankers."""

    @abstractmethod
    async def rerank(
        self,
        query: str,
        results: List[RetrievalResult],
        top_n: int = 5,
    ) -> List[RetrievalResult]:
        """Rerank a list of candidate RetrievalResults for the query."""
        pass


class PassThroughReranker(BaseReranker):
    """Fallback / passthrough reranker that preserves existing retrieval ordering."""

    async def rerank(
        self,
        query: str,
        results: List[RetrievalResult],
        top_n: int = 5,
    ) -> List[RetrievalResult]:
        return results[:top_n]


class FlashRankReranker(BaseReranker):
    """Local, ultra-fast Cross-Encoder reranker powered by FlashRank (ONNX)."""

    def __init__(self, model_name: str = "ms-marco-TinyBERT-L-2-v2"):
        self.model_name = model_name
        self._ranker = None
        self._fallback = PassThroughReranker()
        self._init_ranker()

    def _init_ranker(self) -> None:
        try:
            from flashrank import Ranker

            logger.info(f"Initializing FlashRank with model '{self.model_name}'...")
            self._ranker = Ranker(model_name=self.model_name)
            logger.info("FlashRank cross-encoder initialized successfully.")
        except ImportError:
            logger.warning(
                "flashrank package not installed. Running reranker in passthrough mode."
            )
            self._ranker = None
        except Exception as e:
            logger.warning(
                f"FlashRank initialization failed ({e}). Running in passthrough mode."
            )
            self._ranker = None

    async def rerank(
        self,
        query: str,
        results: List[RetrievalResult],
        top_n: int = 5,
    ) -> List[RetrievalResult]:
        if not results:
            return []

        if len(results) <= 1 or self._ranker is None:
            return results[:top_n]

        try:
            from flashrank import RerankRequest

            passages = [
                {"id": idx, "text": r.content, "meta": r}
                for idx, r in enumerate(results)
            ]

            rerank_request = RerankRequest(query=query, passages=passages)
            ranked_output = self._ranker.rerank(rerank_request)

            reranked_results: List[RetrievalResult] = []
            for item in ranked_output[:top_n]:
                orig_result: RetrievalResult = item["meta"]
                reranked_results.append(
                    RetrievalResult(
                        chunk_id=orig_result.chunk_id,
                        content=orig_result.content,
                        metadata=orig_result.metadata,
                        score=float(item["score"]),
                    )
                )

            logger.info(
                f"FlashRank reranked {len(results)} candidates -> top {len(reranked_results)} returned."
            )
            return reranked_results
        except Exception as e:
            logger.warning(f"FlashRank reranking error: {e}. Falling back to passthrough.")
            return await self._fallback.rerank(query, results, top_n)


class RerankerFactory:
    """Factory to provide the active reranker."""

    _instance: Optional[BaseReranker] = None

    @classmethod
    def get_reranker(cls, force_passthrough: bool = False) -> BaseReranker:
        if force_passthrough:
            return PassThroughReranker()

        if cls._instance is not None:
            return cls._instance

        enable_reranker = getattr(settings, "ENABLE_RERANKER", True)
        if not enable_reranker:
            cls._instance = PassThroughReranker()
        else:
            model_name = getattr(settings, "RERANKER_MODEL", "ms-marco-TinyBERT-L-2-v2")
            cls._instance = FlashRankReranker(model_name=model_name)

        return cls._instance


# Global singleton instance
reranker_service = RerankerFactory.get_reranker()
