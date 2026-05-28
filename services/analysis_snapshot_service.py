# stdlib
from uuid import UUID

# thirdparty
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# project
from db.models.analysis_thread_model import THREAD_STATUS_ACTIVE, AnalysisThread
from db.models.session_model import DreamSession
from services.analysis_policy import ensure_utc
from services.analysis_state_machine_types import SessionSnapshot, ThreadSnapshot


async def build_session_snapshot(db: AsyncSession, session_id: UUID) -> SessionSnapshot:
    """Read-only ORM -> immutable session snapshot. No transaction lifecycle management."""
    session = await db.scalar(select(DreamSession).where(DreamSession.id == session_id))
    if session is None:
        raise ValueError(f"Session {session_id} not found")

    last_activity = session.last_activity_at
    return SessionSnapshot(
        session_id=session.id,
        status=session.status,
        last_activity_at=ensure_utc(last_activity) if last_activity is not None else None,
    )


async def build_thread_snapshot(db: AsyncSession, session_id: UUID) -> ThreadSnapshot:
    """Read-only ORM -> immutable thread snapshot for the current active thread, if any."""
    thread = await db.scalar(
        select(AnalysisThread)
        .where(
            AnalysisThread.session_id == session_id,
            AnalysisThread.status == THREAD_STATUS_ACTIVE,
        )
        .order_by(AnalysisThread.created_at.desc(), AnalysisThread.id.desc())
        .limit(1)
    )
    if thread is None:
        return ThreadSnapshot(
            thread_id=None,
            status=None,
            last_activity_at=None,
            created_at=None,
        )

    last_activity = thread.last_activity_at
    created_at = thread.created_at
    return ThreadSnapshot(
        thread_id=thread.id,
        status=thread.status,
        last_activity_at=ensure_utc(last_activity) if last_activity is not None else None,
        created_at=ensure_utc(created_at) if created_at is not None else None,
    )
