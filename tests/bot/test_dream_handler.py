# stdlib
from unittest.mock import AsyncMock, MagicMock

# thirdparty
import httpx
import pytest

# project
from bot.handlers.dreams import ERROR_TEXT, handle_dream_message

pytestmark = pytest.mark.unit


@pytest.fixture
def fake_message():
    message = MagicMock()
    message.from_user = MagicMock()
    message.from_user.id = 123456789
    message.from_user.first_name = "Анна"
    message.from_user.language_code = "ru"
    message.text = "I dreamed of water"
    message.answer = AsyncMock()
    return message


async def test_telegram_loop_delivers_backend_messages(fake_message, monkeypatch):
    async def mock_create_dream(
        *,
        text: str,
        telegram_id: int,
        telegram_first_name: str | None = None,
        telegram_language_code: str | None = None,
    ) -> list[str]:
        assert text == fake_message.text
        assert telegram_id == fake_message.from_user.id
        assert telegram_first_name == "Анна"
        assert telegram_language_code == "ru"
        return ["Живой ответ от спутника"]

    monkeypatch.setattr("bot.handlers.dreams.create_dream", mock_create_dream)

    await handle_dream_message(fake_message)

    fake_message.answer.assert_awaited_once_with("Живой ответ от спутника")


async def test_telegram_loop_does_not_confirm_on_backend_failure(fake_message, monkeypatch):
    async def mock_create_dream(
        *,
        text: str,
        telegram_id: int,
        telegram_first_name: str | None = None,
        telegram_language_code: str | None = None,
    ) -> None:
        raise httpx.HTTPError("backend unavailable")

    monkeypatch.setattr("bot.handlers.dreams.create_dream", mock_create_dream)

    await handle_dream_message(fake_message)

    fake_message.answer.assert_awaited_once_with(ERROR_TEXT)
