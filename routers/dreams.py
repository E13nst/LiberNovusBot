# thirdparty
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

# project
from db.db_setup import get_session
from db.schemas.dream_schema import DreamCreate, DreamCreateResponse
from services.dream_service import create_dream

dreams_router = APIRouter(tags=["Dreams"])


@dreams_router.post("", response_model=DreamCreateResponse)
async def create_dream_endpoint(
    payload: DreamCreate,
    session: AsyncSession = Depends(get_session),
):
    await create_dream(session=session, user_id=payload.telegram_id, text=payload.text)
    return DreamCreateResponse()
