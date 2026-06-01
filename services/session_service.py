"""Dream session lifecycle with inactivity-based auto-close.

ACTIVE SESSION RULE:
- "active" = row in dream_sessions where status == "active"
- Among multiple active rows for a user, pick the one with the latest created_at
- Session auto-closes when: now() - last_activity_at > INACTIVITY_THRESHOLD
- Every dream creation must call update_session_activity()

FUNCTION CONTRACT:
- get_active_session_raw  — pure read, no mutations, returns stale sessions as-is
- ensure_active_session   — performs inactivity check; closes stale session if needed
- get_or_create_active_session — uses ensure_active_session as the validity gate
"""

# stdlib
from datetime import datetime, timedelta
from uuid import UUID

# thirdparty
from sqlalchemy import update, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

# project
from db.models.session_model import DreamSession

INACTIVITY_THRESHOLD = timedelta(hours=72)

_ACTIVE = "active"
_CLOSED = "closed"


async def update_session_activity(db: AsyncSession, session_id: UUID) -> None:
    await db.execute(
        update(DreamSession)
        .where(DreamSession.id == session_id)
        .values(last_activity_at=func.now())
    )


async def close_session(db: AsyncSession, session_id: UUID) -> None:
    await db.execute(
        update(DreamSession)
        .where(DreamSession.id == session_id)
        .values(status=_CLOSED)
    )


async def get_active_session_raw(db: AsyncSession, user_id: int) -> DreamSession | None:
    """Return the latest active session for user_id. Pure read — no mutations."""
    query = (
        select(DreamSession)
        .where(DreamSession.user_id == user_id, DreamSession.status == _ACTIVE)
        .order_by(DreamSession.created_at.desc())
        .limit(1)
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def ensure_active_session(db: AsyncSession, user_id: int) -> DreamSession | None:
    """Return the active session only if it is within the inactivity threshold.

    If the session is stale (last_activity_at older than INACTIVITY_THRESHOLD),
    close it and return None so the caller can create a fresh session.
    """
    session = await get_active_session_raw(db, user_id)

    if session is None:
        return None

    threshold = datetime.utcnow() - INACTIVITY_THRESHOLD
    if session.last_activity_at < threshold:
        await close_session(db, session.id)
        return None

    return session


async def create_session(db: AsyncSession, user_id: int) -> DreamSession:
    now = datetime.utcnow()
    dream_session = DreamSession(user_id=user_id, status=_ACTIVE, last_activity_at=now)
    db.add(dream_session)
    await db.flush()
    return dream_session


async def get_or_create_active_session(db: AsyncSession, user_id: int) -> DreamSession:
    dream_session = await ensure_active_session(db, user_id)
    if dream_session is not None:
        return dream_session

    return await create_session(db, user_id)
