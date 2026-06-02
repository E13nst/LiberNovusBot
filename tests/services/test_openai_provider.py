# stdlib
import json

# thirdparty
import pytest

# project
from services.config.runtime_config import ConfigValidationError, load_runtime_config
from services.llm_providers.base import (
    ProviderTerminalError,
    ProviderTransportError,
    SDKUnexpectedError,
)
from services.llm_providers import openai_provider as openai_provider_module
from services.llm_providers.openai_provider import OpenAILLMProvider


@pytest.fixture(autouse=True)
def _reset_async_openai_binding():
    openai_provider_module.AsyncOpenAI = None
    yield
    openai_provider_module.AsyncOpenAI = None


def _local_env(**overrides: str) -> dict[str, str]:
    env = {
        "ENV_MODE": "local",
        "LLM_PROVIDER": "openai",
        "OPENAI_API_KEY": "sk-test",
        "OPENAI_BASE_URL": "https://api.openai.com/v1",
        "DEFAULT_MODEL": "gpt-4o-mini",
        "OPENAI_TIMEOUT_SECONDS": "45",
        "DATABASE_URL": "postgresql+asyncpg://postgres:password@localhost:5433/mini_app_db_test",
        "DATABASE_URL_PSYCOPG2": "postgresql+psycopg2://postgres:password@localhost:5433/mini_app_db_test",
        "ANALYSIS_RUNTIME_ENABLED": "false",
    }
    env.update(overrides)
    return env


class _FakeUsage:
    input_tokens = 11
    output_tokens = 22
    total_tokens = 33


class _FakeResponse:
    output_text = json.dumps({"themes": ["integration"]})
    usage = _FakeUsage()


class _FakeResponses:
    def __init__(self):
        self.last_kwargs: dict | None = None

    async def create(self, **kwargs):
        self.last_kwargs = kwargs
        return _FakeResponse()


class _FakeAsyncOpenAI:
    instances: list["_FakeAsyncOpenAI"] = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.responses = _FakeResponses()
        _FakeAsyncOpenAI.instances.append(self)


@pytest.mark.asyncio
async def test_openai_provider_returns_raw_text_and_usage(monkeypatch):
    _FakeAsyncOpenAI.instances.clear()
    monkeypatch.setattr("services.llm_providers.openai_provider.AsyncOpenAI", _FakeAsyncOpenAI)

    config = load_runtime_config(env=_local_env())
    provider = OpenAILLMProvider(config=config)

    result = await provider.generate("compiled prompt", prompt_version="v1")

    assert json.loads(result.raw_text)["themes"] == ["integration"]
    assert result.meta.provider == "openai"
    assert result.meta.model == "gpt-4o-mini"
    assert result.meta.prompt_version == "v1"
    assert result.meta.usage is not None
    assert result.meta.usage.prompt_tokens == 11
    assert result.meta.usage.completion_tokens == 22
    assert result.meta.usage.total_tokens == 33
    assert result.meta.latency_ms >= 0

    client = _FakeAsyncOpenAI.instances[-1]
    assert client.kwargs["api_key"] == "sk-test"
    assert client.kwargs["base_url"] == "https://api.openai.com/v1"
    assert client.kwargs["timeout"] == 45.0
    assert client.responses.last_kwargs is not None
    assert client.responses.last_kwargs["model"] == "gpt-4o-mini"
    assert client.responses.last_kwargs["input"] == "compiled prompt"
    assert client.responses.last_kwargs["text"] == {"format": {"type": "json_object"}}


@pytest.mark.asyncio
async def test_openai_provider_maps_5xx_to_transport_error(monkeypatch):
    class _StatusError(Exception):
        status_code = 503

    class _FailingResponses:
        async def create(self, **kwargs):
            raise _StatusError("upstream unavailable")

    class _Client(_FakeAsyncOpenAI):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.responses = _FailingResponses()

    monkeypatch.setattr("services.llm_providers.openai_provider.AsyncOpenAI", _Client)
    monkeypatch.setattr(
        "services.llm_providers.openai_provider._is_retryable_sdk_error",
        lambda exc: isinstance(exc, _StatusError) and getattr(exc, "status_code", 0) >= 500,
    )

    provider = OpenAILLMProvider(config=load_runtime_config(env=_local_env()))

    with pytest.raises(ProviderTransportError):
        await provider.generate("prompt", prompt_version="v1")


@pytest.mark.asyncio
async def test_openai_provider_maps_4xx_to_terminal_error(monkeypatch):
    class _StatusError(Exception):
        status_code = 401

    class _FailingResponses:
        async def create(self, **kwargs):
            raise _StatusError("unauthorized")

    class _Client(_FakeAsyncOpenAI):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.responses = _FailingResponses()

    monkeypatch.setattr("services.llm_providers.openai_provider.AsyncOpenAI", _Client)
    monkeypatch.setattr(
        "services.llm_providers.openai_provider._is_retryable_sdk_error",
        lambda exc: False,
    )
    monkeypatch.setattr(
        "services.llm_providers.openai_provider._is_terminal_sdk_error",
        lambda exc: isinstance(exc, _StatusError) and getattr(exc, "status_code", 0) == 401,
    )

    provider = OpenAILLMProvider(config=load_runtime_config(env=_local_env()))

    with pytest.raises(ProviderTerminalError):
        await provider.generate("prompt", prompt_version="v1")


@pytest.mark.asyncio
async def test_openai_provider_maps_unexpected_sdk_error(monkeypatch):
    class _FailingResponses:
        async def create(self, **kwargs):
            raise RuntimeError("unexpected sdk shape")

    class _Client(_FakeAsyncOpenAI):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.responses = _FailingResponses()

    monkeypatch.setattr("services.llm_providers.openai_provider.AsyncOpenAI", _Client)

    provider = OpenAILLMProvider(config=load_runtime_config(env=_local_env()))

    with pytest.raises(SDKUnexpectedError):
        await provider.generate("prompt", prompt_version="v1")


def test_openai_provider_rejects_construction_in_test_mode():
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
        OpenAILLMProvider(config=config)
