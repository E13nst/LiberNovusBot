# thirdparty
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

# project
from db.db_setup import get_session
from db.schemas.dream_schema import DreamCreate, DreamCreateResponse
from services.dream_intake import register_incoming_dream

dreams_router = APIRouter(tags=["Dreams"])


@dreams_router.post("", response_model=DreamCreateResponse)
async def create_dream_endpoint(
    payload: DreamCreate,
    db: AsyncSession = Depends(get_session),
):
    await register_incoming_dream(db, telegram_id=payload.telegram_id, text=payload.text)
    return DreamCreateResponse()
