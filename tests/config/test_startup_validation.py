# thirdparty
import pytest

# project
from services.config.runtime_config import load_runtime_config
from services.config.startup_validation import should_start_runtime_worker


def test_runtime_startup_guard_respects_test_mode():
    config = load_runtime_config(
        env={
            "ENV_MODE": "test",
            "LLM_PROVIDER": "openai",
            "DATABASE_URL": "postgresql+asyncpg://postgres:password@localhost:5433/mini_app_db_test",
            "DATABASE_URL_PSYCOPG2": "postgresql+psycopg2://postgres:password@localhost:5433/mini_app_db_test",
            "ANALYSIS_RUNTIME_ENABLED": "true",
        }
    )

    assert should_start_runtime_worker(config) is False
