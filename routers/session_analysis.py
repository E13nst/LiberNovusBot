# stdlib
from typing import Literal
from uuid import UUID

# thirdparty
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

# project
from db.db_setup import get_session
from db.schemas.session_analysis_schema import (
    SessionAnalysisHistorySchema,
    SessionAnalysisSchema,
)
from services.analysis.presentation_service import build_session_analysis_schema
from services.analysis_orchestrator import run_session_analysis
from services.session_analysis_service import get_session_analysis_history

session_analysis_router = APIRouter(tags=["Session Analysis"])

AnalysisModeQuery = Literal["auto", "new", "continue"]


@session_analysis_router.post("/{session_id}/analyze", response_model=SessionAnalysisSchema)
async def analyze_session_endpoint(
    session_id: UUID,
    mode: AnalysisModeQuery = Query(default="auto"),
    db: AsyncSession = Depends(get_session),
):
    saved = await run_session_analysis(db, session_id, mode=mode)
    return build_session_analysis_schema(saved)


@session_analysis_router.get("/{session_id}/analysis", response_model=SessionAnalysisHistorySchema)
async def get_session_analysis_endpoint(
    session_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    history = await get_session_analysis_history(db, session_id)
    if not history.threads:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return history
