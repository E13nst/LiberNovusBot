# project
from services.config.infra_validation import validate_infra
from services.config.runtime_config import RuntimeConfig, get_runtime_config, validate_config


def should_start_runtime_worker(config: RuntimeConfig | None = None) -> bool:
    """Runtime startup guard: decide whether in-process worker may start."""
    resolved = config or get_runtime_config()
    return resolved.runtime_enabled


async def run_startup_validation(config: RuntimeConfig | None = None) -> RuntimeConfig:
    """Run config (pure) + infra (optional) validation before worker startup."""
    resolved = config or get_runtime_config()
    validate_config(resolved)
    await validate_infra(resolved)
    return resolved


def validate_startup_sync(config: RuntimeConfig | None = None) -> RuntimeConfig:
    """Synchronous config validation for prod-check and CLI usage."""
    resolved = config or get_runtime_config()
    validate_config(resolved)
    return resolved
