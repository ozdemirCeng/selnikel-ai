from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, List, Optional


class BaseLLMProvider(ABC):
    """Abstract interface defining the contract for LLM providers.
    Decouples the application from any specific cloud or local LLM vendor.
    """

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        **kwargs,
    ) -> str:
        """Generate a complete text completion asynchronously."""
        pass

    @abstractmethod
    async def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Stream generated text chunks asynchronously."""
        pass

    @abstractmethod
    async def check_health(self) -> bool:
        """Check if the LLM provider service/endpoint is reachable."""
        pass
