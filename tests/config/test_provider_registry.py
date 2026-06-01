# thirdparty
import pytest

# project
from services.config.runtime_config import ConfigValidationError, load_runtime_config
from services.llm_providers.mock_provider import MockLLMProvider
from services.llm_providers.registry import UnknownLLMProviderError, get_provider


def _test_env(**overrides: str) -> dict[str, str]:
    env = {
        "ENV_MODE": "local",
        "LLM_PROVIDER": "mock",
        "DATABASE_URL": "postgresql+asyncpg://postgres:password@localhost:5433/mini_app_db_test",
        "DATABASE_URL_PSYCOPG2": "postgresql+psycopg2://postgres:password@localhost:5433/mini_app_db_test",
        "ANALYSIS_RUNTIME_ENABLED": "false",
    }
    env.update(overrides)
    return env


def test_get_provider_unknown_raises_not_mock_fallback(monkeypatch):
    config = load_runtime_config(env=_test_env())
    monkeypatch.setattr("services.llm_providers.registry.get_runtime_config", lambda: config)

    with pytest.raises(UnknownLLMProviderError):
        get_provider("totally-unknown")


def test_get_provider_blocks_explicit_openai_in_test_mode(monkeypatch):
    config = load_runtime_config(
        env=_test_env(
            ENV_MODE="test",
            LLM_PROVIDER="openai",
            ANALYSIS_RUNTIME_ENABLED="true",
            OPENAI_API_KEY="sk-test",
        )
    )
    monkeypatch.setattr("services.llm_providers.registry.get_runtime_config", lambda: config)

    with pytest.raises(ConfigValidationError, match="ENV_MODE=test"):
        get_provider("openai")


def test_get_provider_returns_mock_for_resolved_test_config(monkeypatch):
    config = load_runtime_config(
        env=_test_env(
            ENV_MODE="test",
            LLM_PROVIDER="openai",
            ANALYSIS_RUNTIME_ENABLED="true",
            OPENAI_API_KEY="sk-test",
        )
    )
    monkeypatch.setattr("services.llm_providers.registry.get_runtime_config", lambda: config)

    provider = get_provider()

    assert config.llm_provider == "mock"
    assert isinstance(provider, MockLLMProvider)
