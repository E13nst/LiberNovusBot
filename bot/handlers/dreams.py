# stdlib
import logging

# thirdparty
import httpx
from aiogram import F, Router
from aiogram.types import Message

# project
from bot.clients.backend_client import create_dream

logger = logging.getLogger(__name__)

router = Router()

ERROR_TEXT = "Не удалось обработать сообщение. Попробуйте позже."


async def _try_send_typing(message: Message) -> None:
    try:
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    except Exception:
        logger.warning(
            "Telegram typing indicator failed",
            extra={"chat_id": message.chat.id},
            exc_info=True,
        )


@router.message(F.text)
async def handle_dream_message(message: Message) -> None:
    if not message.from_user or not message.text:
        return

    await _try_send_typing(message)

    try:
        outbound_messages = await create_dream(
            text=message.text,
            telegram_id=message.from_user.id,
            telegram_first_name=message.from_user.first_name,
            telegram_language_code=message.from_user.language_code,
        )
    except httpx.HTTPError:
        await message.answer(ERROR_TEXT)
        return

    for outbound in outbound_messages:
        await message.answer(outbound)
