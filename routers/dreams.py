# thirdparty
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

# project
from db.db_setup import get_session
from db.schemas.dream_schema import DreamCreate, DreamCreateResponse
from services.runtime.dialogue_router_service import process_incoming_message

dreams_router = APIRouter(tags=["Dreams"])


@dreams_router.post("", response_model=DreamCreateResponse)
async def create_dream_endpoint(
    payload: DreamCreate,
    db: AsyncSession = Depends(get_session),
):
    await process_incoming_message(
        db,
        telegram_id=payload.telegram_id,
        text=payload.text,
    )
    return DreamCreateResponse()
