# stdlib
from typing import Protocol

DELIVERY_LOCK_KEY_PREFIX = "delivery:key:"
DELIVERY_LOCK_TTL_SECONDS = 86400


class DeliveryLockRedis(Protocol):
    async def set(self, key: str, value: str, *, nx: bool = False, ex: int | None = None) -> bool | None: ...


def delivery_lock_key(job_id: str) -> str:
    return f"{DELIVERY_LOCK_KEY_PREFIX}{job_id}"


async def acquire_delivery_lock(redis: DeliveryLockRedis, job_id: str) -> bool:
    """Acquire at-most-once delivery lock for a completed analysis job."""
    result = await redis.set(
        delivery_lock_key(job_id),
        "1",
        nx=True,
        ex=DELIVERY_LOCK_TTL_SECONDS,
    )
    return bool(result)
