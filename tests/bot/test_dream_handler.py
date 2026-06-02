# stdlib
from unittest.mock import AsyncMock, MagicMock

# thirdparty
import httpx
import pytest

# project
from bot.handlers.dreams import CONFIRMATION_TEXT, ERROR_TEXT, handle_dream_message

pytestmark = pytest.mark.unit


@pytest.fixture
def fake_message():
    message = MagicMock()
    message.from_user = MagicMock()
    message.from_user.id = 123456789
    message.text = "I dreamed of water"
    message.answer = AsyncMock()
    return message


async def test_telegram_loop_enqueues_analysis_job(fake_message, monkeypatch):
    backend_called = False

    async def mock_create_dream(*, text: str, telegram_id: int) -> None:
        nonlocal backend_called
        backend_called = True
        assert text == fake_message.text
        assert telegram_id == fake_message.from_user.id

    monkeypatch.setattr("bot.handlers.dreams.create_dream", mock_create_dream)

    await handle_dream_message(fake_message)

    assert backend_called is True
    fake_message.answer.assert_awaited_once_with(CONFIRMATION_TEXT)


async def test_telegram_loop_does_not_confirm_on_backend_failure(fake_message, monkeypatch):
    async def mock_create_dream(*, text: str, telegram_id: int) -> None:
        raise httpx.HTTPError("backend unavailable")

    monkeypatch.setattr("bot.handlers.dreams.create_dream", mock_create_dream)

    await handle_dream_message(fake_message)

    fake_message.answer.assert_awaited_once_with(ERROR_TEXT)


async def test_telegram_loop_ignores_message_without_user(fake_message):
    fake_message.from_user = None

    await handle_dream_message(fake_message)

    fake_message.answer.assert_not_awaited()
