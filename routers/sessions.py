# stdlib
from uuid import UUID

# thirdparty
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

# project
from db.db_setup import get_session
from db.schemas.session_summary_schema import SessionSummarySchema
from services.session_summary_service import (
    build_session_summary,
    get_session_summary,
    save_session_summary,
)

sessions_router = APIRouter(tags=["Sessions"])


@sessions_router.get("/{session_id}/summary", response_model=SessionSummarySchema)
async def get_session_summary_endpoint(
    session_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    summary = await get_session_summary(db, session_id)
    if summary is not None:
        return summary

    summary = await build_session_summary(db, session_id)
    return await save_session_summary(db, summary)
