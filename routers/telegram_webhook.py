# thirdparty
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

# project
from db.db_setup import get_session
from db.schemas.telegram_webhook_schema import TelegramUpdate, TelegramWebhookResponse
from services.dream_intake import register_incoming_dream

telegram_webhook_router = APIRouter(tags=["Telegram"])


@telegram_webhook_router.post("/webhook", response_model=TelegramWebhookResponse)
async def telegram_webhook(
    update: TelegramUpdate,
    db: AsyncSession = Depends(get_session),
) -> TelegramWebhookResponse:
    """Accept Telegram Bot API update JSON and enqueue dream analysis via intake."""
    if update.message is None:
        return TelegramWebhookResponse()

    await register_incoming_dream(
        db,
        telegram_id=update.message.from_user.id,
        text=update.message.text,
    )
    return TelegramWebhookResponse()
