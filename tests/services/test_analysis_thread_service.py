# stdlib
from datetime import datetime

# thirdparty
import pytest
from sqlalchemy import func, select

# project
from db.models.analysis_thread_model import AnalysisThread
from db.models.session_analysis_model import SessionAnalysis
from db.models.session_model import DreamSession
from services.analysis_thread_service import (
    attach_analysis,
    create_thread,
    get_active_thread,
    next_continuation_index,
    save_analysis_in_thread,
)

pytestmark = pytest.mark.integration

SAMPLE_ANALYSIS_JSON = {
    "archetypes": [{"name": "Shadow", "confidence": 0.8, "evidence": ["test"]}],
    "themes": ["transition"],
    "psychodynamic_tension": "tension",
    "compensatory_function": "function",
    "interpretation": "interp",
    "questions_for_user": ["q1"],
}


async def _session(db_session, user_id, *, status: str = "active") -> DreamSession:
    session = DreamSession(user_id=user_id, status=status)
    db_session.add(session)
    await db_session.flush()
    return session


async def test_create_thread_supersedes_previous_active_threads(db_session, user_id):
    session = await _session(db_session, user_id)
    first = await create_thread(db_session, session.id)
    second = await create_thread(db_session, session.id)

    await db_session.refresh(first)
    assert first.status == "idle"
    assert second.status == "active"


async def test_single_active_thread_invariant(db_session, user_id):
    session = await _session(db_session, user_id)
    await create_thread(db_session, session.id)
    await create_thread(db_session, session.id)

    active_count = await db_session.scalar(
        select(func.count())
        .select_from(AnalysisThread)
        .where(
            AnalysisThread.session_id == session.id,
            AnalysisThread.status == "active",
        )
    )
    assert active_count == 1


async def test_get_active_thread_returns_latest_active(db_session, user_id):
    session = await _session(db_session, user_id)
    await create_thread(db_session, session.id)
    latest = await create_thread(db_session, session.id)

    active = await get_active_thread(db_session, session.id)
    assert active is not None
    assert active.id == latest.id


async def test_only_one_is_latest_true_per_thread(db_session, user_id):
    session = await _session(db_session, user_id)
    thread = await create_thread(db_session, session.id)

    first = await save_analysis_in_thread(
        db_session,
        thread,
        session_id=session.id,
        user_id=user_id,
        provider="mock",
        model="mock-v1",
        prompt_version="v1",
        analysis_version="v1",
        analysis_json=SAMPLE_ANALYSIS_JSON,
    )
    second = await save_analysis_in_thread(
        db_session,
        thread,
        session_id=session.id,
        user_id=user_id,
        provider="mock",
        model="mock-v1",
        prompt_version="v1",
        analysis_version="v1",
        analysis_json=SAMPLE_ANALYSIS_JSON,
    )

    latest_count = await db_session.scalar(
        select(func.count())
        .select_from(SessionAnalysis)
        .where(SessionAnalysis.thread_id == thread.id, SessionAnalysis.is_latest.is_(True))
    )
    assert latest_count == 1

    await db_session.refresh(first)
    await db_session.refresh(second)
    assert first.is_latest is False
    assert second.is_latest is True


async def test_continuation_index_increments_on_same_thread(db_session, user_id):
    session = await _session(db_session, user_id)
    thread = await create_thread(db_session, session.id)

    first = await save_analysis_in_thread(
        db_session,
        thread,
        session_id=session.id,
        user_id=user_id,
        provider="mock",
        model="mock-v1",
        prompt_version="v1",
        analysis_version="v1",
        analysis_json=SAMPLE_ANALYSIS_JSON,
    )
    second = await save_analysis_in_thread(
        db_session,
        thread,
        session_id=session.id,
        user_id=user_id,
        provider="mock",
        model="mock-v1",
        prompt_version="v1",
        analysis_version="v1",
        analysis_json=SAMPLE_ANALYSIS_JSON,
    )

    assert first.continuation_index == 0
    assert second.continuation_index == 1
    assert await next_continuation_index(db_session, thread.id) == 2


async def test_multiple_threads_can_each_have_is_latest(db_session, user_id):
    session = await _session(db_session, user_id)
    thread_a = await create_thread(db_session, session.id)
    thread_b = await create_thread(db_session, session.id)

    await save_analysis_in_thread(
        db_session,
        thread_a,
        session_id=session.id,
        user_id=user_id,
        provider="mock",
        model="mock-v1",
        prompt_version="v1",
        analysis_version="v1",
        analysis_json=SAMPLE_ANALYSIS_JSON,
    )
    await save_analysis_in_thread(
        db_session,
        thread_b,
        session_id=session.id,
        user_id=user_id,
        provider="mock",
        model="mock-v1",
        prompt_version="v1",
        analysis_version="v1",
        analysis_json=SAMPLE_ANALYSIS_JSON,
    )

    latest_per_thread = await db_session.scalar(
        select(func.count())
        .select_from(SessionAnalysis)
        .where(SessionAnalysis.session_id == session.id, SessionAnalysis.is_latest.is_(True))
    )
    assert latest_per_thread == 2


async def test_attach_analysis_updates_thread_last_analysis_id(db_session, user_id):
    session = await _session(db_session, user_id)
    thread = await create_thread(db_session, session.id)
    analysis = SessionAnalysis(
        session_id=session.id,
        user_id=user_id,
        thread_id=thread.id,
        provider="mock",
        model="mock-v1",
        prompt_version="v1",
        analysis_version="v1",
        analysis_json=SAMPLE_ANALYSIS_JSON,
        is_latest=False,
        continuation_index=0,
    )
    db_session.add(analysis)
    await db_session.flush()

    await attach_analysis(db_session, thread.id, analysis.id)

    await db_session.refresh(thread)
    await db_session.refresh(analysis)
    assert thread.last_analysis_id == analysis.id
    assert analysis.is_latest is True
