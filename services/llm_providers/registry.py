# project
from services.config.runtime_config import RuntimeConfig, get_runtime_config
from services.config.runtime_guards import assert_llm_provider_allowed
from services.llm_providers.base import LLMProvider
from services.llm_providers.mock_provider import MockLLMProvider
from services.llm_providers.openai_compatible_provider import OpenAICompatibleLLMProvider
from services.llm_providers.openai_provider import OpenAILLMProvider


class UnknownLLMProviderError(ValueError):
    """Raised when provider name is not registered."""


def get_provider(name: str | None = None) -> LLMProvider:
    config = get_runtime_config()
    provider_name = (name or config.llm_provider).strip().lower()
    return _build_provider(provider_name, config)


def _build_provider(provider_name: str, config: RuntimeConfig) -> LLMProvider:
    assert_llm_provider_allowed(provider_name, config)
    if provider_name == "openai":
        return OpenAILLMProvider(config=config)
    if provider_name in {"openai-compatible", "local", "openrouter", "lm-studio", "ollama"}:
        return OpenAICompatibleLLMProvider(
            model_name=config.default_model,
            base_url=config.local_llm_base_url,
            api_key=config.openai_api_key or "",
            provider_name=provider_name,
        )
    if provider_name == "mock":
        return MockLLMProvider()

    raise UnknownLLMProviderError(f"Unknown LLM provider '{provider_name}'")
