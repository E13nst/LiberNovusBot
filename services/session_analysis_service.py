# stdlib
from collections import defaultdict
from datetime import datetime
from uuid import UUID

# thirdparty
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# project
from db.models.analysis_thread_model import THREAD_STATUS_ACTIVE, AnalysisThread
from db.models.session_analysis_model import SessionAnalysis
from db.schemas.session_analysis_schema import (
    SessionAnalysisHistorySchema,
    SessionAnalysisItemSchema,
    SessionAnalysisThreadGroupSchema,
)


async def get_session_analysis(db: AsyncSession, session_id: UUID) -> SessionAnalysis | None:
    """Return the most recently created analysis for a session (any thread)."""
    query = (
        select(SessionAnalysis)
        .where(SessionAnalysis.session_id == session_id)
        .order_by(
            SessionAnalysis.created_at.desc(),
            SessionAnalysis.continuation_index.desc(),
            SessionAnalysis.id.desc(),
        )
        .limit(1)
    )
    return await db.scalar(query)


async def list_session_analyses(db: AsyncSession, session_id: UUID) -> list[SessionAnalysis]:
    query = (
        select(SessionAnalysis)
        .where(SessionAnalysis.session_id == session_id)
        .order_by(SessionAnalysis.thread_id.asc(), SessionAnalysis.created_at.asc())
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def list_session_threads(db: AsyncSession, session_id: UUID) -> list[AnalysisThread]:
    query = (
        select(AnalysisThread)
        .where(AnalysisThread.session_id == session_id)
        .order_by(AnalysisThread.created_at.asc())
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_session_analysis_history(
    db: AsyncSession,
    session_id: UUID,
) -> SessionAnalysisHistorySchema:
    """Read-only grouped history; does not compute is_latest."""
    analyses = await list_session_analyses(db, session_id)
    threads = await list_session_threads(db, session_id)
    thread_status = {thread.id: thread.status for thread in threads}

    grouped: dict[UUID, list[SessionAnalysis]] = defaultdict(list)
    for analysis in analyses:
        grouped[analysis.thread_id].append(analysis)

    sortable_groups: list[tuple[datetime, SessionAnalysisThreadGroupSchema]] = []
    for thread_id, thread_analyses in grouped.items():
        sorted_analyses = sorted(thread_analyses, key=lambda row: row.created_at)
        latest_created_at = sorted_analyses[-1].created_at
        sortable_groups.append(
            (
                latest_created_at,
                SessionAnalysisThreadGroupSchema(
                    thread_id=thread_id,
                    status=thread_status.get(thread_id, THREAD_STATUS_ACTIVE),
                    analyses=[
                        SessionAnalysisItemSchema.model_validate(row) for row in sorted_analyses
                    ],
                ),
            )
        )

    sortable_groups.sort(key=lambda item: item[0], reverse=True)
    thread_groups = [group for _, group in sortable_groups]

    return SessionAnalysisHistorySchema(session_id=session_id, threads=thread_groups)
