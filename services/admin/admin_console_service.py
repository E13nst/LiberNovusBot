from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.analysis_job_model import AnalysisJob
from db.models.dialogue_policy_trace_model import DialoguePolicyTrace
from db.models.dream_model import Dream
from db.models.session_analysis_model import SessionAnalysis
from db.models.session_model import DreamSession
from db.schemas.admin_schema import (
    AdminDreamView,
    AdminEventListResponse,
    AdminPolicyTraceListResponse,
    AdminPolicyTraceView,
    AdminSessionDetail,
    AdminSessionListItem,
    AdminTraceResponse,
    EventView,
)

_EVENT_ORDER = {
    "INPUT": 0,
    "POLICY": 1,
    "CLARIFICATION": 2,
    "DREAM_CREATED": 3,
    "JOB_ENQUEUED": 4,
    "REFLECTION_READY": 5,
}


async def list_admin_sessions(db: AsyncSession) -> list[AdminSessionListItem]:
    rows = await db.execute(
        select(
            DreamSession,
            func.count(func.distinct(Dream.id)).label("dream_count"),
            func.count(func.distinct(AnalysisJob.id)).label("job_count"),
            func.count(func.distinct(SessionAnalysis.id)).label("analysis_count"),
        )
        .outerjoin(Dream, Dream.session_id == DreamSession.id)
        .outerjoin(AnalysisJob, AnalysisJob.session_id == DreamSession.id)
        .outerjoin(SessionAnalysis, SessionAnalysis.session_id == DreamSession.id)
        .group_by(DreamSession.id)
        .order_by(DreamSession.created_at.desc(), DreamSession.id.desc())
    )
    return [
        _session_item(
            session,
            dream_count=dream_count,
            job_count=job_count,
            analysis_count=analysis_count,
        )
        for session, dream_count, job_count, analysis_count in rows.all()
    ]


async def get_admin_session(db: AsyncSession, session_id: UUID) -> AdminSessionDetail | None:
    row = (
        await db.execute(
            select(
                DreamSession,
                func.count(func.distinct(Dream.id)).label("dream_count"),
                func.count(func.distinct(AnalysisJob.id)).label("job_count"),
                func.count(func.distinct(SessionAnalysis.id)).label("analysis_count"),
                func.count(func.distinct(DialoguePolicyTrace.id)).label("policy_trace_count"),
            )
            .outerjoin(Dream, Dream.session_id == DreamSession.id)
            .outerjoin(AnalysisJob, AnalysisJob.session_id == DreamSession.id)
            .outerjoin(SessionAnalysis, SessionAnalysis.session_id == DreamSession.id)
            .outerjoin(DialoguePolicyTrace, DialoguePolicyTrace.session_id == DreamSession.id)
            .where(DreamSession.id == session_id)
            .group_by(DreamSession.id)
        )
    ).first()
    if row is None:
        return None
    session, dream_count, job_count, analysis_count, policy_trace_count = row
    item = _session_item(
        session,
        dream_count=dream_count,
        job_count=job_count,
        analysis_count=analysis_count,
    )
    return AdminSessionDetail(
        **item.model_dump(),
        policy_trace_count=policy_trace_count,
    )


async def list_admin_session_dreams(db: AsyncSession, session_id: UUID) -> list[AdminDreamView] | None:
    if await db.get(DreamSession, session_id) is None:
        return None
    rows = await db.execute(
        select(Dream).where(Dream.session_id == session_id).order_by(Dream.created_at.asc(), Dream.id.asc())
    )
    return [AdminDreamView.model_validate(row) for row in rows.scalars().all()]


async def list_admin_users(db: AsyncSession) -> list:
    from db.schemas.admin_schema import AdminUserListItem

    rows = await db.execute(
        select(
            DreamSession.user_id,
            func.count(func.distinct(DreamSession.id)).label("session_count"),
            func.count(func.distinct(Dream.id)).label("dream_count"),
            func.max(DreamSession.last_activity_at).label("last_activity_at"),
        )
        .outerjoin(Dream, Dream.session_id == DreamSession.id)
        .group_by(DreamSession.user_id)
        .order_by(func.max(DreamSession.last_activity_at).desc().nullslast())
    )
    return [
        AdminUserListItem(
            user_id=user_id,
            session_count=session_count,
            dream_count=dream_count,
            last_activity_at=last_activity_at,
        )
        for user_id, session_count, dream_count, last_activity_at in rows.all()
    ]


async def list_admin_all_dreams(db: AsyncSession, *, limit: int = 200) -> list[AdminDreamView]:
    rows = await db.execute(
        select(Dream).order_by(Dream.created_at.desc(), Dream.id.desc()).limit(limit)
    )
    return [AdminDreamView.model_validate(row) for row in rows.scalars().all()]


async def get_admin_dream(db: AsyncSession, dream_id: int) -> AdminDreamView | None:
    dream = await db.get(Dream, dream_id)
    if dream is None:
        return None
    return AdminDreamView.model_validate(dream)


async def list_admin_policy_traces(db: AsyncSession, session_id: UUID) -> AdminPolicyTraceListResponse | None:
    if await db.get(DreamSession, session_id) is None:
        return None
    rows = await db.execute(
        select(DialoguePolicyTrace)
        .where(DialoguePolicyTrace.session_id == session_id)
        .order_by(DialoguePolicyTrace.created_at.asc(), DialoguePolicyTrace.id.asc())
    )
    return AdminPolicyTraceListResponse(
        session_id=session_id,
        policy_traces=[_policy_trace_view(row) for row in rows.scalars().all()],
    )


async def build_admin_events(db: AsyncSession, session_id: UUID) -> AdminEventListResponse | None:
    session = await db.get(DreamSession, session_id)
    if session is None:
        return None

    dreams = await _session_dreams(db, session_id)
    jobs = await _session_jobs(db, session_id)
    analyses = await _session_analyses(db, session_id)
    traces = await _session_policy_traces(db, session_id)
    dream_by_id = {dream.id: dream for dream in dreams}
    events: list[EventView] = []

    for trace in traces:
        dream = dream_by_id.get(trace.dream_id)
        events.append(
            EventView(
                id=f"policy:{trace.id}:input",
                type="INPUT",
                timestamp=trace.created_at,
                session_id=session_id,
                user_id=trace.user_id,
                payload={
                    "policy_input": trace.input_json,
                    "dream_id": trace.dream_id,
                    "text": dream.text if dream is not None else None,
                },
            )
        )
        events.append(
            EventView(
                id=f"policy:{trace.id}:decision",
                type="POLICY",
                timestamp=trace.created_at,
                session_id=session_id,
                user_id=trace.user_id,
                payload={
                    "decision": trace.decision_json,
                    "outcome": trace.outcome_json,
                },
            )
        )
        if trace.route == "ROUTE_CLARIFICATION":
            events.append(
                EventView(
                    id=f"policy:{trace.id}:clarification",
                    type="CLARIFICATION",
                    timestamp=trace.created_at,
                    session_id=session_id,
                    user_id=trace.user_id,
                    payload=trace.outcome_json,
                )
            )

    for dream in dreams:
        events.append(
            EventView(
                id=f"dream:{dream.id}",
                type="DREAM_CREATED",
                timestamp=dream.created_at,
                session_id=session_id,
                user_id=dream.user_id,
                payload={"dream_id": dream.id, "text": dream.text},
            )
        )

    for job in jobs:
        events.append(
            EventView(
                id=f"job:{job.id}",
                type="JOB_ENQUEUED",
                timestamp=job.created_at,
                session_id=session_id,
                user_id=session.user_id,
                payload={
                    "job_id": str(job.id),
                    "status": job.status,
                    "provider": job.provider,
                    "model": job.model,
                    "mode": job.mode,
                    "attempts": job.attempts,
                    "last_error_class": job.last_error_class,
                    "last_error_message": job.last_error_message,
                },
            )
        )

    for analysis in analyses:
        events.append(
            EventView(
                id=f"analysis:{analysis.id}",
                type="REFLECTION_READY",
                timestamp=analysis.created_at,
                session_id=session_id,
                user_id=analysis.user_id,
                payload={
                    "analysis_id": str(analysis.id),
                    "analysis_job_id": str(analysis.analysis_job_id) if analysis.analysis_job_id else None,
                    "thread_id": str(analysis.thread_id),
                    "analysis_version": analysis.analysis_version,
                    "prompt_version": analysis.prompt_version,
                    "analysis_json": analysis.analysis_json,
                },
            )
        )

    events.sort(key=lambda event: (event.timestamp, _EVENT_ORDER[event.type], event.id))
    return AdminEventListResponse(session_id=session_id, events=events)


async def build_admin_trace(db: AsyncSession, session_id: UUID) -> AdminTraceResponse | None:
    events = await build_admin_events(db, session_id)
    if events is None:
        return None
    return AdminTraceResponse(session_id=session_id, timeline=events.events)


def _session_item(
    session: DreamSession,
    *,
    dream_count: int,
    job_count: int,
    analysis_count: int,
) -> AdminSessionListItem:
    return AdminSessionListItem(
        id=session.id,
        user_id=session.user_id,
        status=session.status,
        created_at=session.created_at,
        updated_at=session.updated_at,
        last_activity_at=session.last_activity_at,
        dream_count=dream_count,
        job_count=job_count,
        analysis_count=analysis_count,
    )


def _policy_trace_view(trace: DialoguePolicyTrace) -> AdminPolicyTraceView:
    return AdminPolicyTraceView(
        id=trace.id,
        session_id=trace.session_id,
        user_id=trace.user_id,
        route=trace.route,
        reason_code=trace.reason_code,
        input=trace.input_json,
        decision=trace.decision_json,
        outcome=trace.outcome_json,
        dream_id=trace.dream_id,
        job_id=trace.job_id,
        created_at=trace.created_at,
    )


async def _session_dreams(db: AsyncSession, session_id: UUID) -> list[Dream]:
    rows = await db.execute(
        select(Dream).where(Dream.session_id == session_id).order_by(Dream.created_at.asc(), Dream.id.asc())
    )
    return list(rows.scalars().all())


async def _session_jobs(db: AsyncSession, session_id: UUID) -> list[AnalysisJob]:
    rows = await db.execute(
        select(AnalysisJob).where(AnalysisJob.session_id == session_id).order_by(AnalysisJob.created_at.asc())
    )
    return list(rows.scalars().all())


async def _session_analyses(db: AsyncSession, session_id: UUID) -> list[SessionAnalysis]:
    rows = await db.execute(
        select(SessionAnalysis).where(SessionAnalysis.session_id == session_id).order_by(SessionAnalysis.created_at.asc())
    )
    return list(rows.scalars().all())


async def _session_policy_traces(db: AsyncSession, session_id: UUID) -> list[DialoguePolicyTrace]:
    rows = await db.execute(
        select(DialoguePolicyTrace)
        .where(DialoguePolicyTrace.session_id == session_id)
        .order_by(DialoguePolicyTrace.created_at.asc(), DialoguePolicyTrace.id.asc())
    )
    return list(rows.scalars().all())
