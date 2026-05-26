# thirdparty
import pytest
from sqlalchemy import func, select

# project
from db.models.dream_model import Dream
from db.models.session_model import DreamSession
from services.dream_intake import register_incoming_dream


pytestmark = pytest.mark.integration


async def test_first_dream_creates_new_session_and_links_it(db_session, user_id):
    dream = await register_incoming_dream(db_session, telegram_id=user_id, text="I saw the sea")
    session_count = await db_session.scalar(
        select(func.count(DreamSession.id)).where(DreamSession.user_id == user_id)
    )

    assert session_count == 1
    assert dream.session_id is not None
    assert dream.user_id == user_id


async def test_second_dream_for_same_user_reuses_session(db_session, user_id):
    first = await register_incoming_dream(db_session, telegram_id=user_id, text="first")
    second = await register_incoming_dream(db_session, telegram_id=user_id, text="second")
    session_count = await db_session.scalar(
        select(func.count(DreamSession.id)).where(DreamSession.user_id == user_id)
    )

    assert first.session_id == second.session_id
    assert session_count == 1


async def test_dreams_for_different_users_get_separate_sessions(db_session, user_id):
    first = await register_incoming_dream(db_session, telegram_id=user_id, text="first")
    second = await register_incoming_dream(db_session, telegram_id=user_id + 1, text="second")

    assert first.session_id != second.session_id


async def test_dream_after_closed_session_creates_new_one(db_session, user_id):
    closed = DreamSession(user_id=user_id, status="closed")
    db_session.add(closed)
    await db_session.flush()

    dream = await register_incoming_dream(db_session, telegram_id=user_id, text="after close")
    active_count = await db_session.scalar(
        select(func.count(DreamSession.id)).where(
            DreamSession.user_id == user_id,
            DreamSession.status == "active",
        )
    )

    assert dream.session_id != closed.id
    assert active_count == 1


async def test_register_incoming_dream_persists_dream_row(db_session, user_id):
    dream = await register_incoming_dream(db_session, telegram_id=user_id, text="persisted")
    saved = await db_session.get(Dream, dream.id)

    assert saved is not None
    assert saved.session_id == dream.session_id
