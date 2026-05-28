# stdlib
from datetime import datetime
from typing import Literal
from uuid import UUID

# thirdparty
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# project
from db.models.analysis_thread_model import AnalysisThread
from db.models.session_analysis_model import SessionAnalysis
from services.analysis_policy import utc_now
from services.analysis_snapshot_service import build_session_snapshot, build_thread_snapshot
from services.analysis_state_machine_service import (
    AnalysisModeRequest,
    normalized_transition,
    resolve_thread_decision,
)
from services.analysis_state_machine_types import (
    DecisionAction,
    ResolvedThreadResult,
    StateMachineConcurrencyError,
)
from services.analysis_thread_service import apply_transition_tx
from services.session_service import INACTIVITY_THRESHOLD

AnalysisModeDecision = Literal["new_thread", "continue_thread"]


async def get_latest_analysis_for_session(
    db: AsyncSession,
    session_id: UUID,
) -> SessionAnalysis | None:
    query = (
        select(SessionAnalysis)
        .where(SessionAnalysis.session_id == session_id)
        .order_by(SessionAnalysis.created_at.desc(), SessionAnalysis.id.desc())
        .limit(1)
    )
    return await db.scalar(query)


def _decision_to_mode(decision_action: DecisionAction) -> AnalysisModeDecision:
    if decision_action == DecisionAction.CONTINUE:
        return "continue_thread"
    return "new_thread"


async def resolve_thread_for_analysis(
    db: AsyncSession,
    session_id: UUID,
    mode: AnalysisModeRequest,
    *,
    now: datetime | None = None,
) -> tuple[AnalysisThread, AnalysisModeDecision]:
    """Orchestration entry: snapshot -> decision -> transition -> apply with bounded re-resolve."""
    now_utc = now or utc_now()
    reresolve_used = False

    while True:
        session_snapshot = await build_session_snapshot(db, session_id)
        thread_snapshot = await build_thread_snapshot(db, session_id)
        decision = resolve_thread_decision(session_snapshot, thread_snapshot, mode, now_utc)
        transition = normalized_transition(decision)

        try:
            async with db.begin_nested():
                thread = await apply_transition_tx(db, transition, session_id=session_id)
            return thread, _decision_to_mode(decision.action)
        except StateMachineConcurrencyError:
            if reresolve_used:
                raise
            reresolve_used = True
            continue


async def decide_analysis_mode(db: AsyncSession, session_id: UUID) -> AnalysisModeDecision:
    """Backward-compatible mode decision using pure state machine snapshots."""
    session_snapshot = await build_session_snapshot(db, session_id)
    thread_snapshot = await build_thread_snapshot(db, session_id)
    decision = resolve_thread_decision(session_snapshot, thread_snapshot, "auto", utc_now())
    return _decision_to_mode(decision.action)


async def resolve_analysis_mode(
    db: AsyncSession,
    session_id: UUID,
    requested: AnalysisModeRequest,
) -> AnalysisModeDecision:
    session_snapshot = await build_session_snapshot(db, session_id)
    thread_snapshot = await build_thread_snapshot(db, session_id)
    decision = resolve_thread_decision(session_snapshot, thread_snapshot, requested, utc_now())
    return _decision_to_mode(decision.action)


async def prepare_thread_for_mode(
    db: AsyncSession,
    session_id: UUID,
    mode: AnalysisModeDecision,
) -> AnalysisThread:
    """Resolve thread via orchestration for legacy callers."""
    requested: AnalysisModeRequest
    if mode == "continue_thread":
        requested = "continue"
    elif mode == "new_thread":
        requested = "new"
    else:
        requested = "auto"
    thread, _ = await resolve_thread_for_analysis(db, session_id, requested)
    return thread


async def resolve_thread_result(
    db: AsyncSession,
    session_id: UUID,
    mode: AnalysisModeRequest,
    *,
    now: datetime | None = None,
) -> ResolvedThreadResult:
    thread, mode_resolved = await resolve_thread_for_analysis(db, session_id, mode, now=now)
    return ResolvedThreadResult(thread_id=thread.id, mode_resolved=mode_resolved)


# Re-export for tests/documentation
INACTIVITY_THRESHOLD_HOURS = INACTIVITY_THRESHOLD
