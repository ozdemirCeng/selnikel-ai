from typing import Optional
from app.core.config import settings
from app.core.logging import logger
from app.services.llm.base import BaseLLMProvider
from app.services.llm.gemini_provider import GeminiProvider
from app.services.llm.ollama_provider import OllamaProvider
from app.services.llm.openai_provider import OpenAIProvider


class LLMProviderFactory:
    """Factory to instantiate the configured LLM provider dynamically."""

    @staticmethod
    def get_provider(provider_type: Optional[str] = None) -> BaseLLMProvider:
        selected_provider = (provider_type or settings.LLM_PROVIDER).lower()

        if selected_provider == "gemini":
            logger.info(f"Instantiating Gemini LLM provider (model={settings.GEMINI_MODEL})")
            return GeminiProvider()
        elif selected_provider == "ollama":
            logger.info(f"Instantiating Ollama LLM provider (model={settings.OLLAMA_MODEL})")
            return OllamaProvider()
        elif selected_provider == "openai":
            logger.info(f"Instantiating OpenAI LLM provider (model={settings.LLM_MODEL})")
            return OpenAIProvider()
        else:
            logger.warning(
                f"Unknown LLM_PROVIDER '{selected_provider}', falling back to GeminiProvider"
            )
            return GeminiProvider()


# Singleton default provider
llm_provider = LLMProviderFactory.get_provider()
