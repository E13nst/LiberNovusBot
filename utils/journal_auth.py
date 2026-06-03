# thirdparty
from fastapi import Header, HTTPException, status


async def require_journal_user_id(
    x_telegram_user_id: int | None = Header(default=None, alias="X-Telegram-User-Id"),
) -> int:
    """Journal API user scope (MVP: trusted header; Mini App initData wiring is follow-up)."""
    if x_telegram_user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="UNAUTHORIZED")
    return int(x_telegram_user_id)
