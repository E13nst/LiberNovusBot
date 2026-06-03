# stdlib
from unittest.mock import AsyncMock, MagicMock, patch

# thirdparty
import pytest

# project
from bot.clients.backend_client import create_dream

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_create_dream_sends_telegram_profile_fields_in_payload():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"messages": ["ok"]}

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("bot.clients.backend_client.httpx.AsyncClient", return_value=mock_client):
        await create_dream(
            text="сон про воду",
            telegram_id=123,
            telegram_first_name="Анна",
            telegram_language_code="ru",
        )

    mock_client.post.assert_awaited_once()
    call_kwargs = mock_client.post.await_args.kwargs
    assert call_kwargs["json"] == {
        "text": "сон про воду",
        "telegram_id": 123,
        "telegram_first_name": "Анна",
        "telegram_language_code": "ru",
    }
