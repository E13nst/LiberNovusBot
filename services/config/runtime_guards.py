# stdlib
import os
from typing import Any

# thirdparty
import httpx

# project
from services.config.runtime_config import ConfigValidationError, EnvMode, RuntimeConfig

_original_async_client_init: Any | None = None
_original_sync_client_init: Any | None = None
_kill_switch_env_mode: EnvMode | None = None


class NetworkDisabledInTestModeError(RuntimeError):
    """Raised when test mode blocks network-capable HTTP client creation."""


def assert_llm_provider_allowed(provider_name: str, config: RuntimeConfig) -> None:
    """Reject non-mock provider selection in test mode."""
    if config.env_mode != "test":
        return
    if provider_name.strip().lower() != "mock":
        raise ConfigValidationError(
            f"ENV_MODE=test forbids LLM_PROVIDER='{provider_name}'; only mock is allowed"
        )


def assert_openai_client_allowed(config: RuntimeConfig) -> None:
    """Reject OpenAI client construction in test mode."""
    if config.env_mode == "test":
        raise ConfigValidationError("ENV_MODE=test forbids AsyncOpenAI instantiation")


def install_test_mode_network_kill_switch(*, env_mode: EnvMode | None = None) -> None:
    """Patch httpx client constructors to block network in test mode."""
    global _original_async_client_init, _original_sync_client_init, _kill_switch_env_mode

    resolved_mode = env_mode or os.environ.get("ENV_MODE", "local").strip().lower()
    if resolved_mode not in ("local", "test", "prod"):
        resolved_mode = "local"
    _kill_switch_env_mode = resolved_mode  # type: ignore[assignment]

    if _original_async_client_init is None:
        _original_async_client_init = httpx.AsyncClient.__init__
        _original_sync_client_init = httpx.Client.__init__

        def _guarded_async_init(client_self, *args, **kwargs):
            _raise_if_test_network_blocked()
            return _original_async_client_init(client_self, *args, **kwargs)

        def _guarded_sync_init(client_self, *args, **kwargs):
            _raise_if_test_network_blocked()
            return _original_sync_client_init(client_self, *args, **kwargs)

        httpx.AsyncClient.__init__ = _guarded_async_init  # type: ignore[method-assign]
        httpx.Client.__init__ = _guarded_sync_init  # type: ignore[method-assign]


def _raise_if_test_network_blocked() -> None:
    if _kill_switch_env_mode == "test":
        raise NetworkDisabledInTestModeError("ENV_MODE=test blocks HTTP client creation")
