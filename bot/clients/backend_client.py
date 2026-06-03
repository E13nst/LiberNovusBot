# thirdparty
import httpx

# project
from bot.config import BACKEND_URL


async def create_dream(
    text: str,
    telegram_id: int,
    *,
    telegram_first_name: str | None = None,
    telegram_language_code: str | None = None,
) -> list[str]:
    payload: dict[str, str | int] = {"text": text, "telegram_id": telegram_id}
    if telegram_first_name is not None:
        payload["telegram_first_name"] = telegram_first_name
    if telegram_language_code is not None:
        payload["telegram_language_code"] = telegram_language_code
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BACKEND_URL}/dreams",
            json=payload,
            timeout=30.0,
        )
        response.raise_for_status()
        payload = response.json()
        return list(payload.get("messages") or [])
