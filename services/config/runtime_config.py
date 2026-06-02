# stdlib
import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

EnvMode = Literal["local", "test", "prod"]

KNOWN_LLM_PROVIDERS = frozenset(
    {
        "mock",
        "openai",
        "openai-compatible",
        "local",
        "openrouter",
        "lm-studio",
        "ollama",
    }
)

OPENAI_COMPATIBLE_PROVIDERS = frozenset({"openai-compatible", "local", "openrouter", "lm-studio", "ollama"})


class ConfigValidationError(ValueError):
    """Raised when runtime configuration violates mode or safety rules."""


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    env_mode: EnvMode
    llm_provider: str
    openai_api_key: str | None
    openai_base_url: str
    local_llm_base_url: str
    default_model: str
    llm_max_attempts: int
    openai_timeout_seconds: float
    runtime_enabled: bool
    analysis_worker_concurrency: int
    analysis_worker_batch_size: int
    analysis_worker_poll_interval: float
    analysis_job_max_attempts: int
    analysis_job_stale_timeout_seconds: int
    database_url: str
    database_url_psycopg2: str
    traceback_output_enabled: bool
    otlp_grpc_endpoint: str


_runtime_config: RuntimeConfig | None = None


def get_runtime_config() -> RuntimeConfig:
    """Return immutable runtime config initialized once per process."""
    global _runtime_config
    if _runtime_config is None:
        _runtime_config = load_runtime_config()
    return _runtime_config


def load_runtime_config(*, env: Mapping[str, str] | None = None) -> RuntimeConfig:
    """Resolve and validate runtime configuration.

    When ``env`` is omitted, result is cached as the process singleton.
    When ``env`` is provided (tests), returns an isolated config without mutating cache.
    """
    global _runtime_config
    config = _resolve_runtime_config(env)
    validate_config(config)
    if env is None:
        _runtime_config = config
    return config


def _resolve_runtime_config(env: Mapping[str, str] | None) -> RuntimeConfig:
    source = os.environ if env is None else env
    env_mode = _parse_env_mode(source.get("ENV_MODE", "local"))

    llm_provider = source.get("LLM_PROVIDER", "mock").strip().lower()
    runtime_enabled = _parse_bool(source.get("ANALYSIS_RUNTIME_ENABLED"), default=False)
    openai_api_key = _optional_str(source.get("OPENAI_API_KEY"))
    openai_base_url = source.get("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
    local_llm_base_url = source.get("LOCAL_LLM_BASE_URL", "http://localhost:1234/v1").strip()
    default_model = source.get("DEFAULT_MODEL", "gpt-4o-mini").strip()
    llm_max_attempts = _parse_int(source.get("LLM_MAX_ATTEMPTS"), default=2, minimum=1)
    openai_timeout_seconds = _parse_float(source.get("OPENAI_TIMEOUT_SECONDS"), default=30.0, minimum=1.0)

    database_url = _require_str(source, "DATABASE_URL")
    database_url_psycopg2 = _require_str(source, "DATABASE_URL_PSYCOPG2")

    if env_mode == "test":
        llm_provider = "mock"
        runtime_enabled = False
        openai_api_key = None

    return RuntimeConfig(
        env_mode=env_mode,
        llm_provider=llm_provider,
        openai_api_key=openai_api_key,
        openai_base_url=openai_base_url,
        local_llm_base_url=local_llm_base_url,
        default_model=default_model,
        llm_max_attempts=llm_max_attempts,
        openai_timeout_seconds=openai_timeout_seconds,
        runtime_enabled=runtime_enabled,
        analysis_worker_concurrency=_parse_int(source.get("ANALYSIS_WORKER_CONCURRENCY"), default=1, minimum=1),
        analysis_worker_batch_size=_parse_int(source.get("ANALYSIS_WORKER_BATCH_SIZE"), default=1, minimum=1),
        analysis_worker_poll_interval=_parse_float(source.get("ANALYSIS_WORKER_POLL_INTERVAL"), default=1.0, minimum=0.01),
        analysis_job_max_attempts=_parse_int(source.get("ANALYSIS_JOB_MAX_ATTEMPTS"), default=1, minimum=1),
        analysis_job_stale_timeout_seconds=_parse_int(
            source.get("ANALYSIS_JOB_STALE_TIMEOUT_SECONDS"),
            default=180,
            minimum=1,
        ),
        database_url=database_url,
        database_url_psycopg2=database_url_psycopg2,
        traceback_output_enabled=_parse_bool(source.get("TRACEBACK_OUTPUT_ENABLED"), default=False),
        otlp_grpc_endpoint=source.get("OTLP_GRPC_ENDPOINT", "http://localhost:4317").strip(),
    )


def validate_config(config: RuntimeConfig) -> None:
    """Pure config validation: no network or DB calls."""
    if config.env_mode not in ("local", "test", "prod"):
        raise ConfigValidationError(f"Invalid ENV_MODE: {config.env_mode}")

    if config.llm_provider not in KNOWN_LLM_PROVIDERS:
        raise ConfigValidationError(
            f"Invalid LLM_PROVIDER '{config.llm_provider}'. Allowed: {sorted(KNOWN_LLM_PROVIDERS)}"
        )

    _validate_url(config.openai_base_url, field_name="OPENAI_BASE_URL")
    _validate_url(config.local_llm_base_url, field_name="LOCAL_LLM_BASE_URL")

    if not config.database_url:
        raise ConfigValidationError("DATABASE_URL is required")
    if not config.database_url_psycopg2:
        raise ConfigValidationError("DATABASE_URL_PSYCOPG2 is required")

    if config.env_mode == "test":
        if config.llm_provider != "mock":
            raise ConfigValidationError("ENV_MODE=test requires LLM_PROVIDER=mock")
        if config.runtime_enabled:
            raise ConfigValidationError("ENV_MODE=test requires ANALYSIS_RUNTIME_ENABLED=false")
        return

    if config.env_mode == "prod":
        _validate_prod_config(config)
        return

    _validate_local_config(config)


def _validate_prod_config(config: RuntimeConfig) -> None:
    if not config.openai_api_key:
        raise ConfigValidationError("ENV_MODE=prod requires OPENAI_API_KEY")
    if config.llm_provider == "mock":
        raise ConfigValidationError("ENV_MODE=prod forbids LLM_PROVIDER=mock")
    if not config.runtime_enabled:
        raise ConfigValidationError("ENV_MODE=prod requires ANALYSIS_RUNTIME_ENABLED=true")
    if config.llm_provider in OPENAI_COMPATIBLE_PROVIDERS and not config.openai_api_key:
        raise ConfigValidationError("OpenAI-compatible provider in prod requires OPENAI_API_KEY")


def _validate_local_config(config: RuntimeConfig) -> None:
    if config.llm_provider == "openai" and not config.openai_api_key:
        logger.warning("ENV_MODE=local with LLM_PROVIDER=openai but OPENAI_API_KEY is missing")
    if config.llm_provider in OPENAI_COMPATIBLE_PROVIDERS and not config.openai_api_key:
        logger.warning(
            "ENV_MODE=local with LLM_PROVIDER=%s but OPENAI_API_KEY is missing",
            config.llm_provider,
        )


def _parse_env_mode(raw: str) -> EnvMode:
    value = raw.strip().lower()
    if value not in ("local", "test", "prod"):
        raise ConfigValidationError(f"Invalid ENV_MODE '{raw}'. Allowed: local, test, prod")
    return value  # type: ignore[return-value]


def _parse_bool(raw: str | None, *, default: bool) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"true", "1", "yes"}


def _parse_int(raw: str | None, *, default: int, minimum: int) -> int:
    if raw is None:
        value = default
    else:
        value = int(raw)
    if value < minimum:
        raise ConfigValidationError(f"Expected integer >= {minimum}, got {value}")
    return value


def _parse_float(raw: str | None, *, default: float, minimum: float) -> float:
    if raw is None:
        value = default
    else:
        value = float(raw)
    if value < minimum:
        raise ConfigValidationError(f"Expected float >= {minimum}, got {value}")
    return value


def _require_str(source: Mapping[str, str], key: str) -> str:
    value = source.get(key, "").strip()
    if not value:
        raise ConfigValidationError(f"{key} is required")
    return value


def _optional_str(raw: str | None) -> str | None:
    if raw is None:
        return None
    value = raw.strip()
    return value or None


def _validate_url(url: str, *, field_name: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ConfigValidationError(f"{field_name} must be a valid http(s) URL, got '{url}'")
