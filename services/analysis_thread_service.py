# stdlib
import uuid
from typing import Any
from uuid import UUID

# thirdparty
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func as sql_func

# project
from db.models.analysis_thread_model import (
    THREAD_STATUS_ACTIVE,
    THREAD_STATUS_CLOSED,
    THREAD_STATUS_IDLE,
    AnalysisThread,
)
from db.models.session_analysis_model import SessionAnalysis
from services.analysis_prepare_result import SessionAnalysisPrepareResult
from services.analysis_policy import utc_now
from services.analysis_state_machine_types import (
    NormalizedTransition,
    StateMachineConcurrencyError,
    TransitionCommandType,
)


async def create_thread(db: AsyncSession, session_id: UUID) -> AnalysisThread:
    await db.execute(
        update(AnalysisThread)
        .where(
            AnalysisThread.session_id == session_id,
            AnalysisThread.status == THREAD_STATUS_ACTIVE,
        )
        .values(status=THREAD_STATUS_IDLE, updated_at=sql_func.now())
    )

    thread = AnalysisThread(session_id=session_id, status=THREAD_STATUS_ACTIVE)
    db.add(thread)
    try:
        await db.flush()
    except IntegrityError as exc:
        raise StateMachineConcurrencyError("Failed to create active thread due to concurrent update") from exc
    return thread


async def get_active_thread(db: AsyncSession, session_id: UUID) -> AnalysisThread | None:
    query = (
        select(AnalysisThread)
        .where(
            AnalysisThread.session_id == session_id,
            AnalysisThread.status == THREAD_STATUS_ACTIVE,
        )
        .order_by(AnalysisThread.created_at.desc(), AnalysisThread.id.desc())
        .limit(1)
    )
    return await db.scalar(query)


async def mark_idle(db: AsyncSession, thread_id: UUID) -> None:
    await db.execute(
        update(AnalysisThread)
        .where(AnalysisThread.id == thread_id)
        .values(status=THREAD_STATUS_IDLE, updated_at=sql_func.now())
    )


async def close_thread(db: AsyncSession, thread_id: UUID) -> None:
    await db.execute(
        update(AnalysisThread)
        .where(AnalysisThread.id == thread_id)
        .values(status=THREAD_STATUS_CLOSED, updated_at=sql_func.now())
    )


async def next_continuation_index(db: AsyncSession, thread_id: UUID) -> int:
    count = await db.scalar(
        select(func.count())
        .select_from(SessionAnalysis)
        .where(SessionAnalysis.thread_id == thread_id)
    )
    return int(count or 0)


async def _clear_latest_for_thread(db: AsyncSession, thread_id: UUID) -> None:
    await db.execute(
        update(SessionAnalysis)
        .where(SessionAnalysis.thread_id == thread_id, SessionAnalysis.is_latest.is_(True))
        .values(is_latest=False)
    )


async def apply_transition_tx(
    db: AsyncSession,
    transition: NormalizedTransition,
    *,
    session_id: UUID,
) -> AnalysisThread:
    """Execute precomputed transition commands only. No policy branching."""
    thread: AnalysisThread | None = None
    for command in transition.commands:
        if command.command_type == TransitionCommandType.CONTINUE:
            if command.thread_id is None:
                raise ValueError("CONTINUE requires thread_id")
            thread = await db.scalar(
                select(AnalysisThread).where(AnalysisThread.id == command.thread_id)
            )
            if thread is None:
                raise StateMachineConcurrencyError(f"Thread {command.thread_id} not found")
            continue

        if command.command_type == TransitionCommandType.MARK_IDLE:
            if command.thread_id is None:
                raise ValueError("MARK_IDLE requires thread_id")
            await mark_idle(db, command.thread_id)
            continue

        if command.command_type == TransitionCommandType.CLOSE_THREAD:
            if command.thread_id is None:
                raise ValueError("CLOSE_THREAD requires thread_id")
            await close_thread(db, command.thread_id)
            continue

        if command.command_type == TransitionCommandType.CREATE_NEW:
            thread = await create_thread(db, session_id)
            continue

        raise ValueError(f"Unknown transition command: {command.command_type}")

    if thread is None:
        raise ValueError("Transition did not resolve to a thread")
    return thread


async def build_session_analysis_row(
    db: AsyncSession,
    prepared: SessionAnalysisPrepareResult,
) -> SessionAnalysis:
    """Assembly phase: build an in-memory session analysis row (not persisted)."""
    continuation_index = await next_continuation_index(db, prepared.thread.id)
    return SessionAnalysis(
        id=uuid.uuid4(),
        session_id=prepared.session_id,
        thread_id=prepared.thread.id,
        user_id=prepared.user_id,
        provider=prepared.provider,
        model=prepared.model,
        prompt_version=prepared.prompt_version,
        analysis_version=prepared.analysis_version,
        analysis_json=prepared.analysis_json,
        raw_response=prepared.raw_response,
        is_latest=True,
        continuation_index=continuation_index,
    )


async def persist_session_analysis_in_thread(
    db: AsyncSession,
    thread: AnalysisThread,
    analysis: SessionAnalysis,
) -> SessionAnalysis:
    """Persistence phase: insert a fully assembled session analysis row."""
    if analysis.thread_id != thread.id:
        raise ValueError("assembled analysis thread_id does not match target thread")
    if analysis.session_id != thread.session_id:
        raise ValueError("assembled analysis session_id does not match target thread session")

    await _clear_latest_for_thread(db, thread.id)
    db.add(analysis)
    await db.flush()

    activity_at = utc_now().replace(tzinfo=None)
    thread.last_analysis_id = analysis.id
    thread.last_activity_at = activity_at
    thread.updated_at = sql_func.now()
    await db.flush()
    return analysis


async def save_analysis_in_thread(
    db: AsyncSession,
    thread: AnalysisThread,
    *,
    session_id: UUID,
    user_id: int,
    provider: str,
    model: str,
    prompt_version: str,
    analysis_version: str,
    analysis_json: dict[str, Any],
    raw_response: str | None = None,
) -> SessionAnalysis:
    """Prepare assembly + persistence for sync/manual paths (no runtime job binding)."""
    prepared = SessionAnalysisPrepareResult(
        thread=thread,
        session_id=session_id,
        user_id=user_id,
        provider=provider,
        model=model,
        prompt_version=prompt_version,
        analysis_version=analysis_version,
        analysis_json=analysis_json,
        raw_response=raw_response,
    )
    analysis = await build_session_analysis_row(db, prepared)
    return await persist_session_analysis_in_thread(db, thread, analysis)


async def attach_analysis(db: AsyncSession, thread_id: UUID, analysis_id: UUID) -> SessionAnalysis:
    """Attach an existing analysis row to a thread and mark it latest."""
    analysis = await db.scalar(select(SessionAnalysis).where(SessionAnalysis.id == analysis_id))
    if analysis is None:
        raise ValueError(f"Analysis {analysis_id} not found")

    thread = await db.scalar(select(AnalysisThread).where(AnalysisThread.id == thread_id))
    if thread is None:
        raise ValueError(f"Thread {thread_id} not found")

    await _clear_latest_for_thread(db, thread_id)
    if analysis.continuation_index == 0 and analysis.thread_id != thread_id:
        analysis.continuation_index = await next_continuation_index(db, thread_id)

    analysis.thread_id = thread_id
    analysis.is_latest = True
    thread.last_analysis_id = analysis.id
    thread.last_activity_at = utc_now().replace(tzinfo=None)
    thread.updated_at = sql_func.now()
    await db.flush()
    return analysis
