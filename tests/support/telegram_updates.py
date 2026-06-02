# stdlib
from typing import Any


def make_telegram_update(*, text: str, user_id: int, update_id: int = 1) -> dict[str, Any]:
    """Synthetic Telegram Bot API update payload for webhook tests."""
    return {
        "update_id": update_id,
        "message": {
            "message_id": 1,
            "from": {"id": user_id, "is_bot": False, "first_name": "Test"},
            "chat": {"id": user_id, "type": "private"},
            "date": 0,
            "text": text,
        },
    }
