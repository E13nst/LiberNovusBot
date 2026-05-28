# stdlib
from typing import Literal
from uuid import UUID

# thirdparty
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

# project
import settings
from db.db_setup import get_session
from db.schemas.analysis_job_schema import (
    AnalysisJobCreateResponseSchema,
    AnalysisJobHistorySchema,
    AnalysisJobSchema,
)
from services.runtime.analysis_job_service import create_job, get_job, list_session_jobs

analysis_jobs_router = APIRouter(tags=["Analysis Jobs"])
AnalysisModeQuery = Literal["auto", "new", "continue"]


@analysis_jobs_router.post(
    "/sessions/{session_id}/analyze-async",
    response_model=AnalysisJobCreateResponseSchema,
)
async def analyze_session_async_endpoint(
    session_id: UUID,
    mode: AnalysisModeQuery = Query(default="auto"),
    db: AsyncSession = Depends(get_session),
):
    job = await create_job(
        db,
        session_id=session_id,
        provider=settings.LLM_PROVIDER,
        model=settings.DEFAULT_MODEL,
        max_attempts=settings.ANALYSIS_JOB_MAX_ATTEMPTS,
        mode=mode,
    )
    return AnalysisJobCreateResponseSchema(job_id=job.id, status=job.status)


@analysis_jobs_router.get("/analysis-jobs/{job_id}", response_model=AnalysisJobSchema)
async def get_analysis_job_endpoint(
    job_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    job = await get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Analysis job not found")
    return job


@analysis_jobs_router.get(
    "/sessions/{session_id}/analysis-jobs",
    response_model=AnalysisJobHistorySchema,
)
async def list_session_analysis_jobs_endpoint(
    session_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    jobs = await list_session_jobs(db, session_id)
    return AnalysisJobHistorySchema(session_id=session_id, jobs=jobs)
