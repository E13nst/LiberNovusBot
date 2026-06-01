# stdlib
import asyncio
import logging

# thirdparty
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# project
from services.config.runtime_config import ConfigValidationError, RuntimeConfig

logger = logging.getLogger(__name__)

DEFAULT_DB_RETRIES = 5
DEFAULT_DB_RETRY_DELAY_SECONDS = 1.0


class InfraValidationError(ConfigValidationError):
    """Raised when optional startup infrastructure checks fail."""


async def validate_infra(config: RuntimeConfig) -> None:
    """Startup-only infrastructure checks (may perform network/DB calls)."""
    if config.env_mode == "prod" and config.runtime_enabled:
        await validate_database_reachable(
            config.database_url,
            retries=DEFAULT_DB_RETRIES,
            retry_delay_seconds=DEFAULT_DB_RETRY_DELAY_SECONDS,
        )


async def validate_database_reachable(
    database_url: str,
    *,
    retries: int = DEFAULT_DB_RETRIES,
    retry_delay_seconds: float = DEFAULT_DB_RETRY_DELAY_SECONDS,
) -> None:
    last_error: Exception | None = None
    engine = create_async_engine(database_url, pool_pre_ping=True)

    try:
        for attempt in range(1, retries + 1):
            try:
                async with engine.connect() as connection:
                    await connection.execute(text("SELECT 1"))
                logger.info("Database reachability check succeeded on attempt %s", attempt)
                return
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Database reachability check failed on attempt %s/%s: %s",
                    attempt,
                    retries,
                    exc,
                )
                if attempt < retries:
                    await asyncio.sleep(retry_delay_seconds)
    finally:
        await engine.dispose()

    raise InfraValidationError(
        f"Database is not reachable after {retries} attempts: {last_error}"
    ) from last_error
