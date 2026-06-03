# thirdparty
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

# project
import settings
from db.db_setup import get_session
from db.schemas.telegram_webhook_schema import TelegramUpdate, TelegramWebhookResponse
from services.ingress.ingress_service import process_incoming_message
from services.notifications.telegram_delivery_service import TelegramDeliveryService

telegram_webhook_router = APIRouter(tags=["Telegram"])


@telegram_webhook_router.post("/webhook", response_model=TelegramWebhookResponse)
async def telegram_webhook(
    update: TelegramUpdate,
    db: AsyncSession = Depends(get_session),
) -> TelegramWebhookResponse:
    """Accept Telegram updates, route through ingress, deliver outbound messages."""
    if update.message is None or not update.message.text:
        return TelegramWebhookResponse()

    result = await process_incoming_message(
        db,
        telegram_id=update.message.from_user.id,
        text=update.message.text,
        user_display_name=update.message.from_user.first_name,
        user_language_code=update.message.from_user.language_code,
    )

    if result.outbound_messages and settings.ENV_MODE != "test":
        delivery = TelegramDeliveryService()
        chat_id = str(update.message.chat.id)
        for message in result.outbound_messages:
            await delivery.send_text(chat_id, message)

    return TelegramWebhookResponse()
