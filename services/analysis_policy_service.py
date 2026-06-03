# project
import settings
from services.llm_providers.base import (
    LLMProvider,
    ProviderRawResponse,
    ProviderTerminalError,
    ProviderTransportError,
    SDKUnexpectedError,
)


async def generate_with_retry(
    llm: LLMProvider,
    prompt: str,
    prompt_version: str,
    logger,
    *,
    temperature: float | None = None,
) -> ProviderRawResponse:
    attempts = max(1, settings.LLM_MAX_ATTEMPTS)
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await llm.generate(
                prompt,
                prompt_version=prompt_version,
                temperature=temperature,
            )
        except ProviderTransportError as exc:
            last_exc = exc
            logger.warning(
                "LLM transport attempt failed",
                extra={
                    "provider": getattr(llm, "provider_name", "unknown"),
                    "model": getattr(llm, "model_name", "unknown"),
                    "prompt_version": prompt_version,
                    "attempt": attempt,
                    "max_attempts": attempts,
                },
            )
            if attempt == attempts:
                raise
        except (ProviderTerminalError, SDKUnexpectedError):
            raise

    if last_exc is not None:
        raise last_exc
    raise RuntimeError("Unreachable retry state")
