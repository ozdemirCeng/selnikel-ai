from typing import Optional
from app.services.retrieval.base import BaseRetriever
from app.services.retrieval.hybrid import QdrantHybridRetriever, hybrid_retriever


class RetrieverFactory:
    """Factory to resolve the active retriever engine."""

    @classmethod
    def get_retriever(cls, retriever_type: str = "hybrid") -> BaseRetriever:
        if retriever_type == "hybrid":
            return hybrid_retriever
        return hybrid_retriever
