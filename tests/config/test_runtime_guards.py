# thirdparty
import httpx
import pytest

# project
from services.config.runtime_config import ConfigValidationError, load_runtime_config
from services.config.runtime_guards import (
    NetworkDisabledInTestModeError,
    assert_llm_provider_allowed,
    install_test_mode_network_kill_switch,
)


def test_registry_blocks_non_mock_provider_in_test_mode():
    config = load_runtime_config(
        env={
            "ENV_MODE": "test",
            "LLM_PROVIDER": "mock",
            "DATABASE_URL": "postgresql+asyncpg://postgres:password@localhost:5433/mini_app_db_test",
            "DATABASE_URL_PSYCOPG2": "postgresql+psycopg2://postgres:password@localhost:5433/mini_app_db_test",
            "ANALYSIS_RUNTIME_ENABLED": "false",
        }
    )

    with pytest.raises(ConfigValidationError, match="ENV_MODE=test"):
        assert_llm_provider_allowed("openai", config)


def test_network_kill_switch_blocks_httpx_client_in_test_mode():
    install_test_mode_network_kill_switch(env_mode="test")

    with pytest.raises(NetworkDisabledInTestModeError):
        httpx.AsyncClient()

    with pytest.raises(NetworkDisabledInTestModeError):
        httpx.Client()


def test_network_kill_switch_allows_httpx_in_local_mode():
    install_test_mode_network_kill_switch(env_mode="local")

    client = httpx.Client()
    client.close()

    install_test_mode_network_kill_switch(env_mode="test")
