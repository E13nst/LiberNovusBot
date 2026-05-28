# stdlib
from datetime import datetime, timedelta

# thirdparty
import pytest

# project
from db.models.dream_model import Dream
from db.models.session_model import DreamSession
from db.models.session_summary_model import SessionSummary
from services.analysis_continuation_service import resolve_analysis_mode
from services.analysis_orchestrator import run_session_analysis
from services.analysis_input_service import AnalysisInputContext
from services.analysis_thread_service import create_thread, get_active_thread
from services.session_analysis_service import get_session_analysis_history
from services.session_service import INACTIVITY_THRESHOLD

pytestmark = pytest.mark.integration


async def _analysis_context(db_session, user_id) -> AnalysisInputContext:
    session = DreamSession(user_id=user_id, status="active")
    db_session.add(session)
    await db_session.flush()

    summary = SessionSummary(
        session_id=session.id,
        user_id=user_id,
        dream_count=1,
        key_symbols=["water"],
        recurring_words=["river"],
        raw_text_sample="I crossed a river",
    )
    dream = Dream(
        user_id=user_id,
        text="I crossed a river in the dark",
        session_id=session.id,
    )
    db_session.add_all([summary, dream])
    await db_session.flush()

    return AnalysisInputContext(session=session, session_summary=summary, dreams=[dream])


async def test_new_session_creates_new_thread(db_session, user_id):
    context = await _analysis_context(db_session, user_id)

    analysis = await run_session_analysis(db_session, context, mode="auto")

    assert analysis.thread_id is not None
    assert analysis.is_latest is True
    assert analysis.continuation_index == 0
    thread = await get_active_thread(db_session, context.session.id)
    assert thread is not None
    assert thread.id == analysis.thread_id


async def test_second_analysis_on_active_session_continues_thread(db_session, user_id):
    context = await _analysis_context(db_session, user_id)
    first = await run_session_analysis(db_session, context, mode="auto")
    second = await run_session_analysis(db_session, context, mode="auto")

    assert first.thread_id == second.thread_id
    assert first.continuation_index == 0
    assert second.continuation_index == 1
    assert first.is_latest is False
    assert second.is_latest is True


async def test_old_analysis_triggers_new_thread(db_session, user_id):
    context = await _analysis_context(db_session, user_id)
    first = await run_session_analysis(db_session, context, mode="auto")

    stale_time = datetime.utcnow() - INACTIVITY_THRESHOLD - timedelta(hours=1)
    first.created_at = stale_time
    thread = await get_active_thread(db_session, context.session.id)
    assert thread is not None
    thread.last_activity_at = stale_time
    await db_session.flush()

    second = await run_session_analysis(db_session, context, mode="auto")

    assert second.thread_id != first.thread_id
    assert second.continuation_index == 0


async def test_mode_new_forces_new_thread(db_session, user_id):
    context = await _analysis_context(db_session, user_id)
    first = await run_session_analysis(db_session, context, mode="auto")
    second = await run_session_analysis(db_session, context, mode="new")

    assert second.thread_id != first.thread_id


async def test_get_history_groups_and_sorts_threads(db_session, user_id):
    context = await _analysis_context(db_session, user_id)
    await run_session_analysis(db_session, context, mode="auto")
    await run_session_analysis(db_session, context, mode="new")

    history = await get_session_analysis_history(db_session, context.session.id)

    assert history.session_id == context.session.id
    assert len(history.threads) == 2
    assert history.threads[0].analyses[-1].is_latest is True
    thread_created = [t.analyses[-1].created_at for t in history.threads]
    assert thread_created == sorted(thread_created, reverse=True)
    for thread in history.threads:
        created_times = [a.created_at for a in thread.analyses]
        assert created_times == sorted(created_times)


async def test_prior_analysis_rows_remain_unchanged_after_new_run(db_session, user_id):
    context = await _analysis_context(db_session, user_id)
    first = await run_session_analysis(db_session, context, mode="auto")
    first_json = dict(first.analysis_json)

    await run_session_analysis(db_session, context, mode="auto")

    await db_session.refresh(first)
    assert first.analysis_json == first_json


async def test_resolve_mode_continue_with_superseded_only_falls_back(db_session, user_id):
    context = await _analysis_context(db_session, user_id)
    thread = await create_thread(db_session, context.session.id)
    thread.status = "idle"
    await db_session.flush()

    assert await resolve_analysis_mode(db_session, context.session.id, "continue") == "new_thread"
