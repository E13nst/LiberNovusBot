# stdlib
from datetime import datetime
import logging
from uuid import UUID

# thirdparty
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# project
from db.models.analysis_job_model import AnalysisJob
from services.analysis_policy import utc_now
from services.runtime.runtime_types import AnalysisJobStatus, InvalidJobTransitionError

logger = logging.getLogger(__name__)


def _naive_now(now: datetime | None = None) -> datetime:
    current = now or utc_now()
    return current.replace(tzinfo=None)


async def create_job(
    db: AsyncSession,
    *,
    session_id: UUID,
    provider: str,
    model: str,
    max_attempts: int,
    mode: str = "auto",
) -> AnalysisJob:
    now = _naive_now()
    job = AnalysisJob(
        session_id=session_id,
        status=AnalysisJobStatus.QUEUED.value,
        provider=provider,
        model=model,
        mode=mode,
        attempts=0,
        max_attempts=max(1, max_attempts),
        retryable=False,
        created_at=now,
        updated_at=now,
        available_after=now,
    )
    db.add(job)
    await db.flush()
    return job


async def acquire_available_jobs(
    db: AsyncSession,
    *,
    limit: int,
    locked_by: str,
    now: datetime | None = None,
) -> list[AnalysisJob]:
    if limit <= 0:
        return []

    acquired_at = _naive_now(now)
    result = await db.execute(
        select(AnalysisJob)
        .where(
            AnalysisJob.status == AnalysisJobStatus.QUEUED.value,
            AnalysisJob.available_after <= acquired_at,
        )
        .order_by(
            AnalysisJob.available_after.asc(),
            AnalysisJob.created_at.asc(),
            AnalysisJob.id.asc(),
        )
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    jobs = list(result.scalars().all())
    for job in jobs:
        job.status = AnalysisJobStatus.RUNNING.value
        job.attempts += 1
        job.updated_at = acquired_at
        job.locked_by = locked_by
        job.locked_at = acquired_at
        if job.started_at is None:
            job.started_at = acquired_at
    await db.flush()
    if jobs:
        logger.info(
            "Analysis runtime acquired jobs",
            extra={
                "worker_id": locked_by,
                "acquired_count": len(jobs),
                "job_ids": [str(job.id) for job in jobs],
                "acquired_at": acquired_at.isoformat(),
                "lock_result": "acquired",
            },
        )
    else:
        logger.debug(
            "Analysis runtime found no acquirable jobs",
            extra={
                "worker_id": locked_by,
                "acquired_count": 0,
                "acquired_at": acquired_at.isoformat(),
                "lock_result": "empty",
            },
        )
    return jobs


async def get_job(db: AsyncSession, job_id: UUID) -> AnalysisJob | None:
    return await db.scalar(select(AnalysisJob).where(AnalysisJob.id == job_id))


async def list_session_jobs(db: AsyncSession, session_id: UUID) -> list[AnalysisJob]:
    result = await db.execute(
        select(AnalysisJob)
        .where(AnalysisJob.session_id == session_id)
        .order_by(AnalysisJob.created_at.desc(), AnalysisJob.id.desc())
    )
    return list(result.scalars().all())


async def mark_completed(
    db: AsyncSession,
    job_id: UUID,
    *,
    thread_id: UUID | None,
    now: datetime | None = None,
) -> AnalysisJob:
    job = await _require_job(db, job_id)
    if job.status != AnalysisJobStatus.RUNNING.value:
        raise InvalidJobTransitionError(f"Cannot complete job in status {job.status}")

    completed_at = _naive_now(now)
    job.status = AnalysisJobStatus.COMPLETED.value
    job.thread_id = thread_id
    job.completed_at = completed_at
    job.updated_at = completed_at
    job.retryable = False
    job.last_error_class = None
    job.last_error_message = None
    job.locked_by = None
    job.locked_at = None
    await db.flush()
    return job


async def mark_failed(
    db: AsyncSession,
    job_id: UUID,
    *,
    error_class: str,
    error_message: str,
    retryable: bool,
    now: datetime | None = None,
) -> AnalysisJob:
    job = await _require_job(db, job_id)
    if job.status != AnalysisJobStatus.RUNNING.value:
        raise InvalidJobTransitionError(f"Cannot fail job in status {job.status}")

    completed_at = _naive_now(now)
    job.status = AnalysisJobStatus.FAILED.value
    job.completed_at = completed_at
    job.updated_at = completed_at
    job.retryable = retryable
    job.last_error_class = error_class
    job.last_error_message = error_message
    job.locked_by = None
    job.locked_at = None
    await db.flush()
    return job


async def requeue(
    db: AsyncSession,
    job_id: UUID,
    *,
    available_after: datetime,
    error_class: str,
    error_message: str,
    now: datetime | None = None,
) -> AnalysisJob:
    job = await _require_job(db, job_id)
    if job.status != AnalysisJobStatus.RUNNING.value:
        raise InvalidJobTransitionError(f"Cannot requeue job in status {job.status}")

    updated_at = _naive_now(now)
    job.status = AnalysisJobStatus.QUEUED.value
    job.available_after = available_after.replace(tzinfo=None)
    job.updated_at = updated_at
    job.retryable = True
    job.last_error_class = error_class
    job.last_error_message = error_message
    job.locked_by = None
    job.locked_at = None
    await db.flush()
    return job


async def _require_job(db: AsyncSession, job_id: UUID) -> AnalysisJob:
    job = await get_job(db, job_id)
    if job is None:
        raise InvalidJobTransitionError(f"Analysis job {job_id} not found")
    return job
