# stdlib
import json

# thirdparty
from fastapi import HTTPException, Request, status

# project
from db.schemas.player_schema import PlayerCreate
from utils.helpers import validate_mini_app_data


async def get_authenticated_player_create(request: Request) -> PlayerCreate:
    """AUTH zone: validate Telegram Mini App initData and build PlayerCreate."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="UNAUTHORIZED")

    init_data = body.get("initData")
    if not init_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="UNAUTHORIZED")

    is_valid, data = validate_mini_app_data(init_data)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="UNAUTHORIZED")

    user = json.loads(data.get("user", "{}"))
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="UNAUTHORIZED")

    username = user.get("username") or body.get("username") or ""

    return PlayerCreate(player_id=user_id, username=username)
