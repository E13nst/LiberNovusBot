# thirdparty
from sqlalchemy.ext.asyncio import AsyncSession

# project
from db.models.dream_model import Dream
from services.dream_service import create_dream
from services.session_service import get_or_create_active_session, update_session_activity


async def register_incoming_dream(db: AsyncSession, telegram_id: int, text: str) -> Dream:
    active_session = await get_or_create_active_session(db, user_id=telegram_id)
    dream = await create_dream(db, user_id=telegram_id, text=text, session_id=active_session.id)
    await update_session_activity(db, active_session.id)
    return dream
