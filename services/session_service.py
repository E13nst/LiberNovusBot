"""Dream session lifecycle.

ACTIVE SESSION RULE (MVP):
- "active" = row in dream_sessions where status == "active"
- Among multiple active rows for a user, pick the one with the latest created_at
- No time-based expiration (no TTL)
- No automatic close on inactivity
- Manual/event-driven close is out of scope for this step
"""

# thirdparty
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# project
from db.models.session_model import DreamSession

_ACTIVE = "active"


async def get_active_session(db: AsyncSession, user_id: int) -> DreamSession | None:
    query = (
        select(DreamSession)
        .where(DreamSession.user_id == user_id, DreamSession.status == _ACTIVE)
        .order_by(DreamSession.created_at.desc())
        .limit(1)
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_session(db: AsyncSession, user_id: int) -> DreamSession:
    dream_session = DreamSession(user_id=user_id, status=_ACTIVE)
    db.add(dream_session)
    await db.flush()
    return dream_session


async def get_or_create_active_session(db: AsyncSession, user_id: int) -> DreamSession:
    dream_session = await get_active_session(db, user_id)
    if dream_session is not None:
        return dream_session

    return await create_session(db, user_id)
