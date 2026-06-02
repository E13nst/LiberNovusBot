# stdlib
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RuntimeDeliveryOverrides:
    redis_client: Any | None = None
    telegram_delivery: Any | None = None


_active: RuntimeDeliveryOverrides | None = None


def get_runtime_delivery_overrides() -> RuntimeDeliveryOverrides | None:
    return _active


@contextmanager
def runtime_delivery_overrides(*, redis_client=None, telegram_delivery=None):
    """Test-only seam: inject delivery fakes without wrapping execute_analysis_job."""
    global _active
    previous = _active
    _active = RuntimeDeliveryOverrides(
        redis_client=redis_client,
        telegram_delivery=telegram_delivery,
    )
    try:
        yield
    finally:
        _active = previous
