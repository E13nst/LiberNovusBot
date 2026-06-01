# thirdparty
import pytest

# project
from services.llm_providers.mock_provider import MockLLMProvider
from services.llm_providers.openai_provider import OpenAILLMProvider
from services.llm_providers.registry import UnknownLLMProviderError, get_provider


def test_registry_returns_openai_provider():
    provider = get_provider("openai")
    assert isinstance(provider, OpenAILLMProvider)


def test_registry_unknown_provider_raises_without_mock_fallback():
    with pytest.raises(UnknownLLMProviderError):
        get_provider("nonexistent-provider")


def test_registry_default_uses_mock_in_test_mode():
    provider = get_provider()
    assert isinstance(provider, MockLLMProvider)
