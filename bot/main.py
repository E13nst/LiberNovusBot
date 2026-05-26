# stdlib
import asyncio
import logging
import sys

# thirdparty
from aiogram import Bot, Dispatcher

# project
from bot.config import BOT_TOKEN
from bot.handlers import dreams

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


async def main() -> None:
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is not set")
        sys.exit(1)

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(dreams.router)

    logger.info("Starting Telegram bot polling")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
