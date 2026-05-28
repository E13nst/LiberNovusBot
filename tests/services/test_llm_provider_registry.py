# project
from services.llm_providers.mock_provider import MockLLMProvider
from services.llm_providers.openai_provider import OpenAILLMProvider
from services.llm_providers.registry import get_provider


def test_registry_returns_openai_provider():
    provider = get_provider("openai")
    assert isinstance(provider, OpenAILLMProvider)


def test_registry_falls_back_to_mock_for_unknown():
    provider = get_provider("nonexistent-provider")
    assert isinstance(provider, MockLLMProvider)
