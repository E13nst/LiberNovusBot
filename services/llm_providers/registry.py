# stdlib
import logging

# project
import settings
from services.llm_providers.base import LLMProvider
from services.llm_providers.mock_provider import MockLLMProvider
from services.llm_providers.openai_compatible_provider import OpenAICompatibleLLMProvider
from services.llm_providers.openai_provider import OpenAILLMProvider

logger = logging.getLogger(__name__)


def get_provider(name: str | None = None) -> LLMProvider:
    provider_name = (name or settings.LLM_PROVIDER).strip().lower()
    if provider_name == "openai":
        return OpenAILLMProvider()
    if provider_name in {"openai-compatible", "local", "openrouter", "lm-studio", "ollama"}:
        return OpenAICompatibleLLMProvider(
            model_name=settings.DEFAULT_MODEL,
            base_url=settings.LOCAL_LLM_BASE_URL,
            api_key=settings.OPENAI_API_KEY,
            provider_name=provider_name,
        )
    if provider_name == "mock":
        return MockLLMProvider()

    logger.warning("Unknown LLM provider '%s', fallback to mock", provider_name)
    return MockLLMProvider()
