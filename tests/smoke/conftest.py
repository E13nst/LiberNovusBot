# stdlib
import os

# thirdparty
import pytest

# project
from services.config.runtime_config import load_runtime_config
from services.config.runtime_guards import install_test_mode_network_kill_switch

SMOKE_DREAM_TEXT = """I dreamed that I was walking through a forest at night.
I found an old abandoned house.
Inside the house there was a staircase leading underground.
I went down into the basement and saw a large black fish.
Then I woke up."""


def openai_smoke_skip_reason() -> str | None:
    """Return skip reason when opt-in OpenAI smoke preconditions are not met."""
    if os.getenv("RUN_OPENAI_SMOKE", "").strip().lower() not in {"true", "1", "yes"}:
        return "RUN_OPENAI_SMOKE is not enabled"

    if os.getenv("ENV_MODE", "").strip().lower() != "local":
        return "ENV_MODE must be local for OpenAI smoke"

    if os.getenv("LLM_PROVIDER", "").strip().lower() != "openai":
        return "LLM_PROVIDER must be openai for OpenAI smoke"

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key or api_key == "sk-test-should-be-ignored":
        return "OPENAI_API_KEY is missing or placeholder"

    return None


@pytest.fixture
def openai_smoke_runtime_config():
    """Isolated local RuntimeConfig for a single live OpenAI inference."""
    reason = openai_smoke_skip_reason()
    if reason is not None:
        pytest.skip(f"OpenAI smoke skipped: {reason}")

    install_test_mode_network_kill_switch(env_mode="local")

    test_db_url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://postgres:password@localhost:5433/mini_app_db_test",
    )
    api_key = os.environ["OPENAI_API_KEY"].strip()
    default_model = os.getenv("DEFAULT_MODEL", "gpt-4o-mini").strip()

    return load_runtime_config(
        env={
            "ENV_MODE": "local",
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": api_key,
            "OPENAI_BASE_URL": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip(),
            "DEFAULT_MODEL": default_model,
            "DATABASE_URL": test_db_url,
            "DATABASE_URL_PSYCOPG2": test_db_url.replace("+asyncpg", "+psycopg2"),
            "ANALYSIS_RUNTIME_ENABLED": "false",
            "LLM_MAX_ATTEMPTS": "1",
        }
    )


def pytest_collection_modifyitems(config, items) -> None:
    """Live OpenAI smoke runs only when explicitly selected via -m openai_smoke."""
    markexpr = getattr(config.option, "markexpr", "") or ""
    smoke_selected = "openai_smoke" in markexpr
    if smoke_selected:
        return

    skip_marker = pytest.mark.skip(
        reason="OpenAI smoke not selected; run with: pytest -m openai_smoke ..."
    )
    for item in items:
        if "openai_smoke" in item.keywords:
            item.add_marker(skip_marker)


@pytest.fixture(autouse=True)
def _require_openai_smoke_env(request):
    """Skip live smoke when opt-in env preconditions are not satisfied."""
    if request.node.get_closest_marker("openai_smoke") is None:
        return
    reason = openai_smoke_skip_reason()
    if reason is not None:
        pytest.skip(f"OpenAI smoke skipped: {reason}")
