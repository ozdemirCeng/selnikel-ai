from typing import Optional
from app.core.config import settings
from app.core.logging import logger
from app.services.embedding.base import BaseEmbeddingProvider
from app.services.embedding.bgem3 import BGEM3EmbeddingProvider
from app.services.embedding.fallback import DeterministicHashEmbeddingProvider


class EmbeddingProviderFactory:
    """Factory to create and resolve the active embedding provider."""

    _instance: Optional[BaseEmbeddingProvider] = None

    @classmethod
    def get_provider(cls, force_provider: Optional[str] = None) -> BaseEmbeddingProvider:
        provider_type = (
            force_provider or getattr(settings, "EMBEDDING_PROVIDER", "bge-m3")
        ).lower()

        if cls._instance is not None and not force_provider:
            return cls._instance

        logger.info(f"Initializing embedding provider: '{provider_type}'")

        if provider_type == "mock" or provider_type == "hash":
            provider = DeterministicHashEmbeddingProvider(
                dimension=getattr(settings, "EMBEDDING_DIMENSION", 1024)
            )
        elif provider_type == "bge-m3":
            provider = BGEM3EmbeddingProvider(
                model_name=getattr(settings, "EMBEDDING_MODEL", "BAAI/bge-m3"),
                device=getattr(settings, "EMBEDDING_DEVICE", "cpu"),
            )
        else:
            logger.warning(
                f"Unknown embedding provider '{provider_type}'. Defaulting to BGE-M3."
            )
            provider = BGEM3EmbeddingProvider()

        if not force_provider:
            cls._instance = provider

        return provider


# Global singleton instance
embedding_provider = EmbeddingProviderFactory.get_provider()
