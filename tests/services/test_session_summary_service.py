# thirdparty
import pytest

# project
from db.models.dream_model import Dream
from db.models.session_model import DreamSession
from routers.sessions import get_session_summary_endpoint
from services.session_summary_service import (
    build_session_summary,
    get_session_summary,
    save_session_summary,
)


pytestmark = pytest.mark.integration


async def test_build_session_summary_aggregates_dream_text(db_session, user_id):
    session = DreamSession(user_id=user_id, status="closed")
    db_session.add(session)
    await db_session.flush()
    db_session.add_all(
        [
            Dream(user_id=user_id, session_id=session.id, text="Forest wolf moon and river"),
            Dream(user_id=user_id, session_id=session.id, text="Wolf river bridge"),
            Dream(user_id=user_id, session_id=session.id, text="Moon tower wolf"),
        ]
    )
    await db_session.flush()

    summary = await build_session_summary(db_session, session.id)

    assert summary.session_id == session.id
    assert summary.user_id == user_id
    assert summary.dream_count == 3
    assert summary.key_symbols[:4] == ["wolf", "moon", "river", "bridge"]
    assert summary.recurring_words == ["wolf", "moon", "river"]
    assert summary.raw_text_sample == (
        "Forest wolf moon and river Wolf river bridge Moon tower wolf"
    )


async def test_build_session_summary_limits_raw_text_sample(db_session, user_id):
    session = DreamSession(user_id=user_id, status="closed")
    db_session.add(session)
    await db_session.flush()
    db_session.add_all(
        [
            Dream(user_id=user_id, session_id=session.id, text="one " * 400),
            Dream(user_id=user_id, session_id=session.id, text="two " * 400),
        ]
    )
    await db_session.flush()

    summary = await build_session_summary(db_session, session.id)

    assert summary.raw_text_sample is not None
    assert len(summary.raw_text_sample) == 1000


async def test_save_session_summary_upserts_by_session_id(db_session, user_id):
    session = DreamSession(user_id=user_id, status="closed")
    db_session.add(session)
    await db_session.flush()
    db_session.add(Dream(user_id=user_id, session_id=session.id, text="wolf river"))
    await db_session.flush()

    first = await build_session_summary(db_session, session.id)
    saved_first = await save_session_summary(db_session, first)
    assert saved_first.dream_count == 1

    db_session.add(Dream(user_id=user_id, session_id=session.id, text="river moon"))
    await db_session.flush()
    second = await build_session_summary(db_session, session.id)
    saved_second = await save_session_summary(db_session, second)

    stored = await get_session_summary(db_session, session.id)
    assert stored is not None
    assert saved_second.id == saved_first.id
    assert stored.id == saved_first.id
    assert stored.dream_count == 2
    assert stored.key_symbols[:3] == ["river", "moon", "wolf"]


async def test_summary_endpoint_builds_and_saves_when_missing(db_session, user_id):
    session = DreamSession(user_id=user_id, status="closed")
    db_session.add(session)
    await db_session.flush()
    db_session.add(Dream(user_id=user_id, session_id=session.id, text="forest moon"))
    await db_session.flush()

    response = await get_session_summary_endpoint(session.id, db_session)
    stored = await get_session_summary(db_session, session.id)

    assert stored is not None
    assert response.id == stored.id
    assert response.dream_count == 1
    assert response.key_symbols == ["forest", "moon"]
