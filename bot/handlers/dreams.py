# thirdparty
import httpx
from aiogram import F, Router
from aiogram.types import Message

# project
from bot.clients.backend_client import create_dream

router = Router()

CONFIRMATION_TEXT = "Сон принят. Я сохранил его в системе."
ERROR_TEXT = "Не удалось сохранить сон. Попробуйте позже."


@router.message(F.text)
async def handle_dream_message(message: Message) -> None:
    if not message.from_user or not message.text:
        return

    try:
        await create_dream(text=message.text, telegram_id=message.from_user.id)
    except httpx.HTTPError:
        await message.answer(ERROR_TEXT)
        return

    await message.answer(CONFIRMATION_TEXT)
