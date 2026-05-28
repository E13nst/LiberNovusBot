# stdlib
from dataclasses import dataclass
from uuid import UUID

# thirdparty
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# project
from db.models.dream_model import Dream
from db.models.session_model import DreamSession
from db.models.session_summary_model import SessionSummary
from services.session_summary_service import (
    build_session_summary,
    get_session_summary,
    save_session_summary,
)


@dataclass(frozen=True)
class AnalysisInputContext:
    session: DreamSession
    session_summary: SessionSummary
    dreams: list[Dream]


async def load_analysis_input(db: AsyncSession, session_id: UUID) -> AnalysisInputContext:
    """Aggregate session, summary, and dreams for analysis orchestration."""
    session = await db.scalar(select(DreamSession).where(DreamSession.id == session_id))
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    summary = await get_session_summary(db, session_id)
    if summary is None:
        summary = await build_session_summary(db, session_id)
        summary = await save_session_summary(db, summary)

    result = await db.execute(
        select(Dream)
        .where(Dream.session_id == session_id)
        .order_by(Dream.created_at.asc(), Dream.id.asc())
    )
    dreams = list(result.scalars().all())

    return AnalysisInputContext(session=session, session_summary=summary, dreams=dreams)
