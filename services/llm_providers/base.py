# stdlib
from abc import ABC, abstractmethod
from dataclasses import dataclass


class ProviderError(RuntimeError):
    """Base provider error."""


class ProviderTransportError(ProviderError):
    """Raised when provider transport/API request fails."""


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
