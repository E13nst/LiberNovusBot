# stdlib
from datetime import datetime, timedelta

# thirdparty
import pytest

# project
from db.models.session_analysis_model import SessionAnalysis
from db.models.session_model import DreamSession
from services.analysis_continuation_service import decide_analysis_mode, resolve_analysis_mode
from services.analysis_thread_service import create_thread
from services.session_service import INACTIVITY_THRESHOLD

pytestmark = pytest.mark.integration

SAMPLE_ANALYSIS_JSON = {
    "archetypes": [{"name": "Shadow", "confidence": 0.8, "evidence": ["test"]}],
    "themes": ["transition"],
    "psychodynamic_tension": "tension",
    "compensatory_function": "function",
    "interpretation": "interp",
    "questions_for_user": ["q1"],
}


async def _add_analysis(
    db_session,
    *,
    session_id,
    user_id,
    thread_id,
    created_at: datetime | None = None,
    is_latest: bool = True,
    continuation_index: int = 0,
) -> SessionAnalysis:
    analysis = SessionAnalysis(
        session_id=session_id,
        user_id=user_id,
        thread_id=thread_id,
        provider="mock",
        model="mock-v1",
        prompt_version="v1",
        analysis_version="v1",
        analysis_json=SAMPLE_ANALYSIS_JSON,
        is_latest=is_latest,
        continuation_index=continuation_index,
    )
    if created_at is not None:
        analysis.created_at = created_at
    db_session.add(analysis)
    await db_session.flush()
    return analysis


async def test_decide_mode_new_thread_when_no_prior_analysis(db_session, user_id):
    session = DreamSession(user_id=user_id, status="active")
    db_session.add(session)
    await db_session.flush()

    assert await decide_analysis_mode(db_session, session.id) == "new_thread"


async def test_decide_mode_new_thread_when_last_analysis_older_than_72h(db_session, user_id):
    session = DreamSession(user_id=user_id, status="active")
    db_session.add(session)
    await db_session.flush()

    thread = await create_thread(db_session, session.id)
    old_time = datetime.utcnow() - INACTIVITY_THRESHOLD - timedelta(hours=1)
    thread.last_activity_at = old_time
    await _add_analysis(
        db_session,
        session_id=session.id,
        user_id=user_id,
        thread_id=thread.id,
        created_at=old_time,
    )
    await db_session.flush()

    assert await decide_analysis_mode(db_session, session.id) == "new_thread"


async def test_decide_mode_continue_when_session_active_and_recent_analysis(db_session, user_id):
    session = DreamSession(user_id=user_id, status="active")
    db_session.add(session)
    await db_session.flush()

    thread = await create_thread(db_session, session.id)
    now = datetime.utcnow()
    thread.last_activity_at = now
    await _add_analysis(
        db_session,
        session_id=session.id,
        user_id=user_id,
        thread_id=thread.id,
        created_at=now,
    )
    await db_session.flush()

    assert await decide_analysis_mode(db_session, session.id) == "continue_thread"


async def test_decide_mode_new_thread_when_session_closed(db_session, user_id):
    session = DreamSession(user_id=user_id, status="closed")
    db_session.add(session)
    await db_session.flush()

    thread = await create_thread(db_session, session.id)
    await _add_analysis(
        db_session,
        session_id=session.id,
        user_id=user_id,
        thread_id=thread.id,
        created_at=datetime.utcnow(),
    )

    assert await decide_analysis_mode(db_session, session.id) == "new_thread"


async def test_resolve_mode_continue_falls_back_to_new_thread_without_active_thread(db_session, user_id):
    session = DreamSession(user_id=user_id, status="active")
    db_session.add(session)
    await db_session.flush()

    assert await resolve_analysis_mode(db_session, session.id, "continue") == "new_thread"


async def test_resolve_mode_auto_delegates_to_decide(db_session, user_id):
    session = DreamSession(user_id=user_id, status="active")
    db_session.add(session)
    await db_session.flush()

    assert await resolve_analysis_mode(db_session, session.id, "auto") == "new_thread"


async def test_resolve_mode_new_always_new_thread(db_session, user_id):
    session = DreamSession(user_id=user_id, status="active")
    db_session.add(session)
    await db_session.flush()

    thread = await create_thread(db_session, session.id)
    await _add_analysis(
        db_session,
        session_id=session.id,
        user_id=user_id,
        thread_id=thread.id,
        created_at=datetime.utcnow(),
    )

    assert await resolve_analysis_mode(db_session, session.id, "new") == "new_thread"
