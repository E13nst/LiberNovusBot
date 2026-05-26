# thirdparty
import httpx

# project
from bot.config import BACKEND_URL


async def create_dream(text: str, telegram_id: int) -> None:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BACKEND_URL}/dreams",
            json={"text": text, "telegram_id": telegram_id},
            timeout=10.0,
        )
        response.raise_for_status()
