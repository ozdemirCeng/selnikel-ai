from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.rag import RetrievalFilter, RetrievalResult


class BaseRetriever(ABC):
    """Abstract interface for all document retrieval services in Selnikel AI."""

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filter_criteria: Optional[RetrievalFilter] = None,
    ) -> List[RetrievalResult]:
        """Retrieve most relevant DomainChunks for a user query."""
        pass
