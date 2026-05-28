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
from services.analysis_input_service import load_analysis_input
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
    context = await load_analysis_input(db, session_id)
    return await run_session_analysis(db, context, mode=mode)


@session_analysis_router.get("/{session_id}/analysis", response_model=SessionAnalysisHistorySchema)
async def get_session_analysis_endpoint(
    session_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    history = await get_session_analysis_history(db, session_id)
    if not history.threads:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return history
