# stdlib
from datetime import datetime, timedelta

# thirdparty
import pytest
from sqlalchemy import func, select

# project
from db.models.session_model import DreamSession
from services.session_service import (
    INACTIVITY_THRESHOLD,
    close_session,
    create_session,
    ensure_active_session,
    get_active_session_raw,
    get_or_create_active_session,
    update_session_activity,
)


pytestmark = pytest.mark.integration


async def test_get_active_raw_returns_none_when_no_sessions(db_session, user_id):
    assert await get_active_session_raw(db_session, user_id) is None


async def test_get_active_raw_returns_existing_active_session(db_session, user_id):
    session = DreamSession(user_id=user_id, status="active")
    db_session.add(session)
    await db_session.flush()

    active = await get_active_session_raw(db_session, user_id)

    assert active is not None
    assert active.id == session.id


async def test_get_active_raw_returns_latest_when_multiple_active(db_session, user_id):
    older = DreamSession(
        user_id=user_id,
        status="active",
        created_at=datetime.utcnow() - timedelta(hours=1),
    )
    newer = DreamSession(user_id=user_id, status="active", created_at=datetime.utcnow())
    db_session.add_all([older, newer])
    await db_session.flush()

    active = await get_active_session_raw(db_session, user_id)

    assert active is not None
    assert active.id == newer.id


async def test_get_active_raw_ignores_non_active_status(db_session, user_id):
    db_session.add(DreamSession(user_id=user_id, status="closed"))
    await db_session.flush()

    assert await get_active_session_raw(db_session, user_id) is None


async def test_get_active_raw_does_not_close_inactive_session(db_session, user_id):
    """get_active_session_raw is a pure read — must never mutate status."""
    stale_time = datetime.utcnow() - INACTIVITY_THRESHOLD - timedelta(hours=1)
    stale = DreamSession(user_id=user_id, status="active", last_activity_at=stale_time)
    db_session.add(stale)
    await db_session.flush()

    result = await get_active_session_raw(db_session, user_id)

    assert result is not None
    assert result.status == "active"


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


# ── Inactivity lifecycle ────────────────────────────────────────────────────


async def test_update_session_activity_updates_timestamp(db_session, user_id):
    old_time = datetime.utcnow() - timedelta(hours=10)
    session = DreamSession(user_id=user_id, status="active", last_activity_at=old_time)
    db_session.add(session)
    await db_session.flush()

    await update_session_activity(db_session, session.id)
    await db_session.refresh(session)

    assert session.last_activity_at > old_time


async def test_close_session_sets_status_to_closed(db_session, user_id):
    session = DreamSession(user_id=user_id, status="active")
    db_session.add(session)
    await db_session.flush()

    await close_session(db_session, session.id)
    await db_session.refresh(session)

    assert session.status == "closed"


async def test_ensure_active_returns_none_for_inactive_session(db_session, user_id):
    stale_time = datetime.utcnow() - INACTIVITY_THRESHOLD - timedelta(hours=1)
    stale = DreamSession(user_id=user_id, status="active", last_activity_at=stale_time)
    db_session.add(stale)
    await db_session.flush()

    result = await ensure_active_session(db_session, user_id)

    assert result is None


async def test_ensure_active_auto_closes_inactive_session(db_session, user_id):
    stale_time = datetime.utcnow() - INACTIVITY_THRESHOLD - timedelta(hours=1)
    stale = DreamSession(user_id=user_id, status="active", last_activity_at=stale_time)
    db_session.add(stale)
    await db_session.flush()

    await ensure_active_session(db_session, user_id)
    await db_session.refresh(stale)

    assert stale.status == "closed"


async def test_ensure_active_returns_session_within_inactivity_threshold(db_session, user_id):
    recent_time = datetime.utcnow() - timedelta(hours=1)
    session = DreamSession(user_id=user_id, status="active", last_activity_at=recent_time)
    db_session.add(session)
    await db_session.flush()

    result = await ensure_active_session(db_session, user_id)

    assert result is not None
    assert result.id == session.id


async def test_get_or_create_creates_new_session_after_inactivity(db_session, user_id):
    stale_time = datetime.utcnow() - INACTIVITY_THRESHOLD - timedelta(hours=1)
    old_session = DreamSession(user_id=user_id, status="active", last_activity_at=stale_time)
    db_session.add(old_session)
    await db_session.flush()

    new_session = await get_or_create_active_session(db_session, user_id)

    assert new_session.id != old_session.id
    assert new_session.status == "active"
