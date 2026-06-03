# stdlib
from typing import Any


def make_telegram_update(
    *,
    text: str,
    user_id: int,
    update_id: int = 1,
    first_name: str = "Test",
    language_code: str = "ru",
) -> dict[str, Any]:
    """Synthetic Telegram Bot API update payload for webhook tests."""
    from_user: dict[str, Any] = {"id": user_id, "is_bot": False, "first_name": first_name}
    if language_code is not None:
        from_user["language_code"] = language_code
    return {
        "update_id": update_id,
        "message": {
            "message_id": 1,
            "from": from_user,
            "chat": {"id": user_id, "type": "private"},
            "date": 0,
            "text": text,
        },
    }
