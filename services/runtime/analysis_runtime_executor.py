# stdlib
from collections.abc import Awaitable, Callable
from datetime import timedelta
import logging

# thirdparty
from sqlalchemy.ext.asyncio import AsyncSession

# project
from db.models.analysis_job_model import AnalysisJob
from db.models.session_analysis_model import SessionAnalysis
from services.analysis_orchestrator import run_session_analysis
from services.analysis_policy import utc_now
from services.runtime.analysis_job_service import mark_completed, mark_failed, requeue
from services.runtime.runtime_types import NonRetryableAnalysisError, RetryableAnalysisError

logger = logging.getLogger(__name__)

AnalysisOrchestrator = Callable[..., Awaitable[SessionAnalysis]]
RETRY_DELAY_SECONDS = 5


async def execute_analysis_job(
    db: AsyncSession,
    job: AnalysisJob,
    *,
    orchestrator: AnalysisOrchestrator = run_session_analysis,
) -> AnalysisJob:
    started_at = utc_now()
    logger.info(
        "Analysis runtime executing job",
        extra={
            "job_id": str(job.id),
            "session_id": str(job.session_id),
            "provider": job.provider,
            "model": job.model,
        },
    )
    try:
        analysis = await orchestrator(db, job.session_id, mode=job.mode)
    except RetryableAnalysisError as exc:
        return await _handle_retryable_failure(db, job, exc, started_at)
    except NonRetryableAnalysisError as exc:
        return await _handle_terminal_failure(db, job, exc, started_at, "NonRetryableAnalysisError")
    except Exception as exc:
        terminal = NonRetryableAnalysisError(str(exc))
        return await _handle_terminal_failure(db, job, terminal, started_at, "NonRetryableAnalysisError")

    completed = await mark_completed(db, job.id, thread_id=analysis.thread_id)
    _log_outcome(completed, started_at, "completed")
    return completed


async def _handle_retryable_failure(
    db: AsyncSession,
    job: AnalysisJob,
    exc: RetryableAnalysisError,
    started_at,
) -> AnalysisJob:
    if job.attempts < job.max_attempts:
        available_after = utc_now().replace(tzinfo=None) + timedelta(seconds=RETRY_DELAY_SECONDS)
        updated = await requeue(
            db,
            job.id,
            available_after=available_after,
            error_class=type(exc).__name__,
            error_message=str(exc),
        )
        _log_outcome(updated, started_at, "requeued")
        return updated

    failed = await mark_failed(
        db,
        job.id,
        error_class=type(exc).__name__,
        error_message=str(exc),
        retryable=True,
    )
    _log_outcome(failed, started_at, "failed")
    return failed


async def _handle_terminal_failure(
    db: AsyncSession,
    job: AnalysisJob,
    exc: NonRetryableAnalysisError,
    started_at,
    error_class: str,
) -> AnalysisJob:
    failed = await mark_failed(
        db,
        job.id,
        error_class=error_class,
        error_message=str(exc),
        retryable=False,
    )
    _log_outcome(failed, started_at, "failed")
    return failed


def _log_outcome(job: AnalysisJob, started_at, outcome: str) -> None:
    latency_ms = int((utc_now() - started_at).total_seconds() * 1000)
    logger.info(
        "Analysis runtime job %s",
        outcome,
        extra={
            "job_id": str(job.id),
            "session_id": str(job.session_id),
            "thread_id": str(job.thread_id) if job.thread_id else None,
            "provider": job.provider,
            "model": job.model,
            "latency_ms": latency_ms,
            "attempts": job.attempts,
            "outcome": outcome,
            "error_class": job.last_error_class,
        },
    )
