# stdlib
import time
from typing import Any

# thirdparty
import httpx

# project
from services.llm_providers.base import (
    LLMProvider,
    ProviderRawResponse,
    ProviderResponseMeta,
    ProviderTransportError,
    ProviderUsage,
)


class OpenAICompatibleLLMProvider(LLMProvider):
    """OpenAI-compatible transport for local servers and gateway providers."""

    def __init__(
        self,
        *,
        model_name: str,
        base_url: str,
        api_key: str = "",
        provider_name: str = "openai-compatible",
        timeout_seconds: float = 30.0,
    ) -> None:
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.provider_name = provider_name
        self.timeout_seconds = timeout_seconds

    async def generate(
        self,
        prompt: str,
        *,
        prompt_version: str,
        temperature: float | None = None,
    ) -> ProviderRawResponse:
        started_at = time.perf_counter()
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0 if temperature is None else temperature,
        }

        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout_seconds) as client:
                response = await client.post("/chat/completions", json=payload, headers=headers)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderTransportError(str(exc)) from exc

        body = response.json()
        content = _extract_content(body)
        return ProviderRawResponse(
            raw_text=content,
            meta=ProviderResponseMeta(
                provider=self.provider_name,
                model=self.model_name,
                prompt_version=prompt_version,
                latency_ms=int((time.perf_counter() - started_at) * 1000),
                usage=_extract_usage(body.get("usage")),
            ),
        )


def _extract_content(body: dict[str, Any]) -> str:
    try:
        message = body["choices"][0]["message"]
        content = message["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderTransportError("Provider response missing chat content") from exc
    if not isinstance(content, str):
        raise ProviderTransportError("Provider content must be string")
    return content


def _extract_usage(raw_usage: Any) -> ProviderUsage | None:
    if not isinstance(raw_usage, dict):
        return None
    prompt_tokens = raw_usage.get("prompt_tokens")
    completion_tokens = raw_usage.get("completion_tokens")
    total_tokens = raw_usage.get("total_tokens")
    if not all(isinstance(v, int) for v in (prompt_tokens, completion_tokens, total_tokens)):
        return None
    return ProviderUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )
