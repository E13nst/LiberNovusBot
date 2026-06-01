# stdlib
import time
from typing import Any

# project
from services.config.runtime_config import RuntimeConfig, get_runtime_config
from services.config.runtime_guards import assert_openai_client_allowed
from services.llm_providers.base import (
    LLMProvider,
    ProviderRawResponse,
    ProviderResponseMeta,
    ProviderTerminalError,
    ProviderTransportError,
    ProviderUsage,
    SDKUnexpectedError,
)

_DEFAULT_TIMEOUT_SECONDS = 30.0

# Monkeypatch target for tests; real class loaded lazily when still None.
AsyncOpenAI: type | None = None


class OpenAILLMProvider(LLMProvider):
    """OpenAI Responses API transport; no parsing or contract validation."""

    provider_name = "openai"

    def __init__(
        self,
        config: RuntimeConfig | None = None,
        *,
        client: Any | None = None,
    ) -> None:
        resolved = config or get_runtime_config()
        assert_openai_client_allowed(resolved)

        self._config = resolved
        self.model_name = resolved.default_model
        self._timeout_seconds = _DEFAULT_TIMEOUT_SECONDS

        if client is not None:
            self._client = client
        else:
            client_cls = _get_async_openai_class()
            self._client = client_cls(
                api_key=resolved.openai_api_key or "",
                base_url=resolved.openai_base_url,
                timeout=self._timeout_seconds,
            )

    async def generate(self, prompt: str, *, prompt_version: str) -> ProviderRawResponse:
        started_at = time.perf_counter()
        try:
            response = await self._client.responses.create(
                model=self.model_name,
                input=prompt,
                text={"format": {"type": "json_object"}},
            )
        except Exception as exc:
            raise _map_sdk_exception(exc) from exc

        raw_text = _extract_output_text(response)
        return ProviderRawResponse(
            raw_text=raw_text,
            meta=ProviderResponseMeta(
                provider=self.provider_name,
                model=self.model_name,
                prompt_version=prompt_version,
                latency_ms=int((time.perf_counter() - started_at) * 1000),
                usage=_extract_usage(getattr(response, "usage", None)),
            ),
        )


def _get_async_openai_class() -> type:
    global AsyncOpenAI
    if AsyncOpenAI is not None:
        return AsyncOpenAI
    from openai import AsyncOpenAI as _AsyncOpenAI

    AsyncOpenAI = _AsyncOpenAI
    return AsyncOpenAI


def _map_sdk_exception(exc: Exception) -> Exception:
    if _is_retryable_sdk_error(exc):
        return ProviderTransportError(str(exc))
    if _is_terminal_sdk_error(exc):
        return ProviderTerminalError(str(exc))
    return SDKUnexpectedError(str(exc))


def _is_retryable_sdk_error(exc: Exception) -> bool:
    api_errors = _openai_api_errors()
    if api_errors is None:
        return False
    api_connection_error, api_timeout_error, api_status_error = api_errors
    if isinstance(exc, (api_connection_error, api_timeout_error)):
        return True
    if isinstance(exc, api_status_error):
        status = exc.status_code
        if status is None:
            return False
        if status >= 500:
            return True
        if status == 429:
            return True
    return False


def _is_terminal_sdk_error(exc: Exception) -> bool:
    api_errors = _openai_api_errors()
    if api_errors is None:
        return False
    _, _, api_status_error = api_errors
    if isinstance(exc, api_status_error):
        status = exc.status_code
        if status is not None and 400 <= status < 500 and status != 429:
            return True
    return False


def _openai_api_errors() -> tuple[type, type, type] | None:
    try:
        from openai import APIConnectionError, APIStatusError, APITimeoutError
    except ImportError:
        return None
    return APIConnectionError, APITimeoutError, APIStatusError


def _extract_output_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    raise SDKUnexpectedError("OpenAI response missing output_text")


def _extract_usage(raw_usage: Any) -> ProviderUsage | None:
    if raw_usage is None:
        return None

    prompt_tokens = getattr(raw_usage, "input_tokens", None)
    if prompt_tokens is None:
        prompt_tokens = getattr(raw_usage, "prompt_tokens", None)

    completion_tokens = getattr(raw_usage, "output_tokens", None)
    if completion_tokens is None:
        completion_tokens = getattr(raw_usage, "completion_tokens", None)

    total_tokens = getattr(raw_usage, "total_tokens", None)

    if not all(isinstance(v, int) for v in (prompt_tokens, completion_tokens, total_tokens)):
        return None

    return ProviderUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )
