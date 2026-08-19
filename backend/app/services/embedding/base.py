from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class BaseEmbeddingProvider(ABC):
    """Abstract interface for all embedding providers in Selnikel AI."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the vector dimensionality (e.g. 1024 for BGE-M3)."""
        pass

    @abstractmethod
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Compute dense vector embeddings for a list of document texts."""
        pass

    @abstractmethod
    async def embed_query(self, text: str) -> List[float]:
        """Compute dense vector embedding for a search query string."""
        pass

    @abstractmethod
    async def embed_sparse(self, texts: List[str]) -> List[Dict[int, float]]:
        """Compute sparse lexical token weights for a list of texts."""
        pass
