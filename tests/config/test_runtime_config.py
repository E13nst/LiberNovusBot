# stdlib
import os

# thirdparty
import pytest

# project
from services.config.runtime_config import (
    ConfigValidationError,
    load_runtime_config,
    validate_config,
)


def _base_env(**overrides: str) -> dict[str, str]:
    env = {
        "ENV_MODE": "local",
        "LLM_PROVIDER": "mock",
        "DATABASE_URL": "postgresql+asyncpg://postgres:password@localhost:5433/mini_app_db_test",
        "DATABASE_URL_PSYCOPG2": "postgresql+psycopg2://postgres:password@localhost:5433/mini_app_db_test",
        "ANALYSIS_RUNTIME_ENABLED": "false",
    }
    env.update(overrides)
    return env


def test_prod_without_openai_api_key_hard_fails():
    env = _base_env(
        ENV_MODE="prod",
        LLM_PROVIDER="openai",
        ANALYSIS_RUNTIME_ENABLED="true",
        OPENAI_API_KEY="",
    )
    with pytest.raises(ConfigValidationError, match="OPENAI_API_KEY"):
        load_runtime_config(env=env)


def test_prod_with_mock_provider_hard_fails():
    env = _base_env(
        ENV_MODE="prod",
        LLM_PROVIDER="mock",
        ANALYSIS_RUNTIME_ENABLED="true",
        OPENAI_API_KEY="sk-test",
    )
    with pytest.raises(ConfigValidationError, match="mock"):
        load_runtime_config(env=env)


def test_prod_requires_runtime_enabled():
    env = _base_env(
        ENV_MODE="prod",
        LLM_PROVIDER="openai",
        ANALYSIS_RUNTIME_ENABLED="false",
        OPENAI_API_KEY="sk-test",
    )
    with pytest.raises(ConfigValidationError, match="ANALYSIS_RUNTIME_ENABLED"):
        load_runtime_config(env=env)


def test_unknown_provider_hard_fails_without_fallback():
    env = _base_env(LLM_PROVIDER="unknown-provider")
    with pytest.raises(ConfigValidationError, match="LLM_PROVIDER"):
        load_runtime_config(env=env)


def test_test_mode_forces_mock_and_disables_runtime():
    env = _base_env(
        ENV_MODE="test",
        LLM_PROVIDER="openai",
        ANALYSIS_RUNTIME_ENABLED="true",
        OPENAI_API_KEY="sk-should-be-ignored",
    )
    config = load_runtime_config(env=env)

    assert config.env_mode == "test"
    assert config.llm_provider == "mock"
    assert config.runtime_enabled is False


def test_invalid_env_mode_hard_fails():
    env = _base_env(ENV_MODE="staging")
    with pytest.raises(ConfigValidationError, match="ENV_MODE"):
        load_runtime_config(env=env)


def test_validate_config_is_pure_no_network(monkeypatch):
    env = _base_env(ENV_MODE="local", LLM_PROVIDER="mock")

    def _forbidden(*args, **kwargs):
        raise AssertionError("config validation must not perform network calls")

    monkeypatch.setattr("socket.create_connection", _forbidden)
    config = load_runtime_config(env=env)
    validate_config(config)
