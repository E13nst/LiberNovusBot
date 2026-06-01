# stdlib
import os

# thirdparty
import pytest

# project
from db.models.dream_model import Dream
from db.models.session_model import DreamSession
from db.models.session_summary_model import SessionSummary
from services.config.runtime_config import load_runtime_config
from services.config.runtime_guards import install_test_mode_network_kill_switch
from services.llm_providers.base import LLMProvider, ProviderRawResponse
from services.llm_providers.openai_provider import OpenAILLMProvider

SMOKE_DREAM_TEXT = """I dreamed that I was walking through a forest at night.
I found an old abandoned house.
Inside the house there was a staircase leading underground.
I went down into the basement and saw a large black fish.
Then I woke up."""


class SingleInferenceOpenAIProvider(LLMProvider):
    """Delegates to OpenAILLMProvider; smoke allows exactly one network inference."""

    def __init__(self, inner: OpenAILLMProvider) -> None:
        self._inner = inner
        self.provider_name = inner.provider_name
        self.model_name = inner.model_name
        self.call_count = 0
        self.last_response: ProviderRawResponse | None = None

    async def generate(self, prompt: str, *, prompt_version: str) -> ProviderRawResponse:
        self.call_count += 1
        if self.call_count > 1:
            raise AssertionError("OpenAI smoke must perform exactly one inference")
        response = await self._inner.generate(prompt, prompt_version=prompt_version)
        self.last_response = response
        return response


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


async def seed_smoke_session(db, user_id: int) -> DreamSession:
    session = DreamSession(user_id=user_id, status="active")
    db.add(session)
    await db.flush()

    db.add(
        SessionSummary(
            session_id=session.id,
            user_id=user_id,
            dream_count=1,
            key_symbols=["forest", "house", "fish"],
            recurring_words=[],
            raw_text_sample=SMOKE_DREAM_TEXT[:120],
        )
    )
    db.add(
        Dream(
            user_id=user_id,
            text=SMOKE_DREAM_TEXT,
            session_id=session.id,
        )
    )
    await db.flush()
    return session


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


@pytest.fixture
def openai_smoke_provider(openai_smoke_runtime_config, monkeypatch):
    """Registry-backed OpenAI provider for runtime/orchestrator smoke paths."""
    import settings

    monkeypatch.setattr(settings, "LLM_MAX_ATTEMPTS", 1)
    inner = OpenAILLMProvider(config=openai_smoke_runtime_config)
    provider = SingleInferenceOpenAIProvider(inner)
    def _get_provider(name=None):
        return provider

    # Orchestrator imports get_provider by reference; patch both call sites.
    monkeypatch.setattr("services.llm_providers.registry.get_provider", _get_provider)
    monkeypatch.setattr("services.analysis_orchestrator.get_provider", _get_provider)
    return provider


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
