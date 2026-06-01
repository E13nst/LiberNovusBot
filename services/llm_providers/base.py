# stdlib
from abc import ABC, abstractmethod
from dataclasses import dataclass


class ProviderError(RuntimeError):
    """Base provider error."""


class ProviderTransportError(ProviderError):
    """Raised when provider transport/API request fails (retryable)."""


class ProviderTerminalError(ProviderError):
    """Raised when provider request fails with a non-retryable API error."""


class SDKUnexpectedError(ProviderTerminalError):
    """Raised when OpenAI SDK fails in an unclassified or unexpected way."""


@dataclass(frozen=True)
class ProviderUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass(frozen=True)
class ProviderResponseMeta:
    provider: str
    model: str
    prompt_version: str
    latency_ms: int
    usage: ProviderUsage | None = None


@dataclass(frozen=True)
class ProviderRawResponse:
    raw_text: str
    meta: ProviderResponseMeta


class LLMProvider(ABC):
    provider_name: str = "unknown"
    model_name: str = "unknown"

    @abstractmethod
    async def generate(self, prompt: str, *, prompt_version: str) -> ProviderRawResponse:
        """Return raw provider text and provider metadata only."""
