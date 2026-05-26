# stdlib
from datetime import datetime, timedelta

# thirdparty
import pytest
from sqlalchemy import func, select

# project
from db.models.session_model import DreamSession
from services.session_service import create_session, get_active_session, get_or_create_active_session


pytestmark = pytest.mark.integration


async def test_get_active_returns_none_when_no_sessions(db_session, user_id):
    assert await get_active_session(db_session, user_id) is None


async def test_get_active_returns_existing_active_session(db_session, user_id):
    session = DreamSession(user_id=user_id, status="active")
    db_session.add(session)
    await db_session.flush()

    active = await get_active_session(db_session, user_id)

    assert active is not None
    assert active.id == session.id


async def test_get_active_returns_latest_when_multiple_active(db_session, user_id):
    older = DreamSession(
        user_id=user_id,
        status="active",
        created_at=datetime.utcnow() - timedelta(hours=1),
    )
    newer = DreamSession(user_id=user_id, status="active", created_at=datetime.utcnow())
    db_session.add_all([older, newer])
    await db_session.flush()

    active = await get_active_session(db_session, user_id)

    assert active is not None
    assert active.id == newer.id


async def test_get_active_ignores_non_active_status(db_session, user_id):
    db_session.add(DreamSession(user_id=user_id, status="closed"))
    await db_session.flush()

    assert await get_active_session(db_session, user_id) is None


async def test_create_session_persists_with_active_status(db_session, user_id):
    session = await create_session(db_session, user_id)

    assert session.user_id == user_id
    assert session.status == "active"
    assert session.id is not None


async def test_get_or_create_creates_when_none_exist(db_session, user_id):
    first = await get_or_create_active_session(db_session, user_id)
    second = await get_or_create_active_session(db_session, user_id)
    count = await db_session.scalar(
        select(func.count(DreamSession.id)).where(DreamSession.user_id == user_id)
    )

    assert first.id == second.id
    assert count == 1


async def test_get_or_create_reuses_existing_active(db_session, user_id):
    existing = DreamSession(user_id=user_id, status="active")
    db_session.add(existing)
    await db_session.flush()

    active = await get_or_create_active_session(db_session, user_id)

    assert active.id == existing.id
