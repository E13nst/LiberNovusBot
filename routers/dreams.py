# thirdparty
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

# project
from db.db_setup import get_session
from db.schemas.dream_schema import DreamCreate, DreamCreateResponse
from services.ingress.ingress_service import process_incoming_message

dreams_router = APIRouter(tags=["Dreams"])


@dreams_router.post("", response_model=DreamCreateResponse)
async def create_dream_endpoint(
    payload: DreamCreate,
    db: AsyncSession = Depends(get_session),
):
    result = await process_incoming_message(
        db,
        telegram_id=payload.telegram_id,
        text=payload.text,
        user_display_name=payload.telegram_first_name,
        user_language_code=payload.telegram_language_code,
    )
    return DreamCreateResponse(
        messages=list(result.outbound_messages),
        session_id=result.session_id,
        dream_id=result.dream_id,
    )
