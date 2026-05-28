# stdlib
import json

# thirdparty
import pytest

# project
from services.llm_providers.openai_compatible_provider import OpenAICompatibleLLMProvider


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class _FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        self.last_payload = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json=None, headers=None):
        self.last_payload = json
        return _FakeResponse(
            {
                "choices": [{"message": {"content": '{"themes": ["x"]}'}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            }
        )


@pytest.mark.asyncio
async def test_openai_compatible_provider_returns_raw_text_and_usage(monkeypatch):
    monkeypatch.setattr("services.llm_providers.openai_compatible_provider.httpx.AsyncClient", _FakeAsyncClient)
    provider = OpenAICompatibleLLMProvider(
        model_name="test-model",
        base_url="http://localhost:1234/v1",
        provider_name="local",
    )

    result = await provider.generate("prompt", prompt_version="v1")

    assert json.loads(result.raw_text)["themes"] == ["x"]
    assert result.meta.provider == "local"
    assert result.meta.model == "test-model"
    assert result.meta.prompt_version == "v1"
    assert result.meta.usage is not None
    assert result.meta.usage.total_tokens == 30
