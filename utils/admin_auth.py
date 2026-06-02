import secrets

from fastapi import Header, HTTPException, status

import settings


async def require_admin_token(x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> None:
    """Protect /admin/api/* with a shared local admin token."""
    expected = settings.ADMIN_TOKEN
    if not x_admin_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin token required")
    if not expected or not secrets.compare_digest(x_admin_token, expected):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin token")
