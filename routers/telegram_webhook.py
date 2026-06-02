# thirdparty
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

# project
from db.db_setup import get_session
from db.schemas.telegram_webhook_schema import TelegramUpdate, TelegramWebhookResponse
from services.runtime.dialogue_router_service import process_incoming_message

telegram_webhook_router = APIRouter(tags=["Telegram"])


@telegram_webhook_router.post("/webhook", response_model=TelegramWebhookResponse)
async def telegram_webhook(
    update: TelegramUpdate,
    db: AsyncSession = Depends(get_session),
) -> TelegramWebhookResponse:
    """Accept Telegram updates and route them through Dialogue Policy."""
    if update.message is None:
        return TelegramWebhookResponse()

    await process_incoming_message(
        db,
        telegram_id=update.message.from_user.id,
        text=update.message.text,
    )
    return TelegramWebhookResponse()
