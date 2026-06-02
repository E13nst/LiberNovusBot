# stdlib
from collections.abc import Awaitable, Callable
from datetime import timedelta
import logging

# thirdparty
from sqlalchemy.ext.asyncio import AsyncSession

# project
import settings
from db.db_setup import redis_connection_pool
from db.models.analysis_job_model import AnalysisJob
from db.models.analysis_thread_model import AnalysisThread
from db.models.session_analysis_model import SessionAnalysis
from redis import asyncio as aioredis
from services.analysis_orchestrator import prepare_session_analysis
from services.analysis_policy import utc_now
from services.analysis_thread_service import build_session_analysis_row, persist_session_analysis_in_thread
from services.notifications.analysis_delivery_service import deliver_completed_analysis
from services.notifications.telegram_delivery_service import TelegramDeliveryService
from services.runtime.analysis_job_service import mark_completed, mark_failed, requeue
from services.runtime.runtime_delivery_overrides import get_runtime_delivery_overrides
from services.runtime.runtime_types import NonRetryableAnalysisError, RetryableAnalysisError

logger = logging.getLogger(__name__)

AnalysisOrchestrator = Callable[..., Awaitable[SessionAnalysis]]
RETRY_DELAY_SECONDS = 5


async def _assemble_runtime_analysis(db: AsyncSession, job: AnalysisJob) -> tuple[SessionAnalysis, AnalysisThread]:
    """Phase 1 — analysis assembly: validate pipeline output and bind job trace link (no persistence)."""
    prepared = await prepare_session_analysis(db, job.session_id, mode=job.mode)
    analysis = await build_session_analysis_row(db, prepared)
    try:
        bound = analysis.with_job_id(job.id)
    except ValueError as exc:
        raise NonRetryableAnalysisError(str(exc)) from exc
    return bound, prepared.thread


async def _persist_runtime_analysis(
    db: AsyncSession,
    thread: AnalysisThread,
    analysis: SessionAnalysis,
) -> SessionAnalysis:
    """Phase 2 — persistence: insert the fully assembled analysis row."""
    return await persist_session_analysis_in_thread(db, thread, analysis)


async def _execute_with_job_binding(db: AsyncSession, job: AnalysisJob) -> SessionAnalysis:
    analysis, thread = await _assemble_runtime_analysis(db, job)
    return await _persist_runtime_analysis(db, thread, analysis)


async def execute_analysis_job(
    db: AsyncSession,
    job: AnalysisJob,
    *,
    orchestrator: AnalysisOrchestrator | None = None,
    redis_client=None,
    telegram_delivery: TelegramDeliveryService | None = None,
) -> AnalysisJob:
    started_at = utc_now()
    logger.info(
        "Analysis runtime executing job",
        extra={
            "job_id": str(job.id),
            "session_id": str(job.session_id),
            "provider": job.provider,
            "model": job.model,
            "locked_by": job.locked_by,
            "attempts": job.attempts,
        },
    )
    try:
        if orchestrator is None:
            analysis = await _execute_with_job_binding(db, job)
        else:
            analysis = await orchestrator(db, job.session_id, mode=job.mode)
    except RetryableAnalysisError as exc:
        return await _handle_retryable_failure(db, job, exc, started_at)
    except NonRetryableAnalysisError as exc:
        return await _handle_terminal_failure(db, job, exc, started_at, "NonRetryableAnalysisError")
    except Exception as exc:
        terminal = NonRetryableAnalysisError(str(exc))
        return await _handle_terminal_failure(db, job, terminal, started_at, "NonRetryableAnalysisError")

    completed = await mark_completed(db, job.id, thread_id=analysis.thread_id)
    _log_outcome(completed, started_at, "completed", analysis=analysis)
    await _deliver_completed_analysis(
        completed,
        analysis,
        redis_client=redis_client,
        telegram_delivery=telegram_delivery,
    )
    return completed


async def _deliver_completed_analysis(
    job: AnalysisJob,
    analysis: SessionAnalysis,
    *,
    redis_client=None,
    telegram_delivery: TelegramDeliveryService | None = None,
) -> None:
    """Best-effort delivery side effect; failures do not affect job completion."""
    overrides = get_runtime_delivery_overrides()
    if redis_client is None and overrides is not None and overrides.redis_client is not None:
        redis_client = overrides.redis_client
    if telegram_delivery is None and overrides is not None and overrides.telegram_delivery is not None:
        telegram_delivery = overrides.telegram_delivery

    if settings.ENV_MODE == "test" and redis_client is None and telegram_delivery is None:
        return

    client = redis_client
    owns_redis = False
    if client is None:
        client = aioredis.Redis(connection_pool=redis_connection_pool, decode_responses=True)
        owns_redis = True

    delivery = telegram_delivery if telegram_delivery is not None else TelegramDeliveryService()
    try:
        await deliver_completed_analysis(job, analysis, redis_client=client, telegram_delivery=delivery)
    finally:
        if owns_redis:
            await client.aclose()


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


def _log_outcome(
    job: AnalysisJob,
    started_at,
    outcome: str,
    *,
    analysis: SessionAnalysis | None = None,
) -> None:
    latency_ms = int((utc_now() - started_at).total_seconds() * 1000)
    extra = {
        "job_id": str(job.id),
        "session_id": str(job.session_id),
        "thread_id": str(job.thread_id) if job.thread_id else None,
        "provider": job.provider,
        "model": job.model,
        "latency_ms": latency_ms,
        "attempts": job.attempts,
        "outcome": outcome,
        "final_state": job.status,
        "error_class": job.last_error_class,
        "locked_by": job.locked_by,
    }
    if analysis is not None:
        analysis_id = getattr(analysis, "id", None)
        if analysis_id is not None:
            extra["analysis_id"] = str(analysis_id)
        analysis_job_id = getattr(analysis, "analysis_job_id", None)
        if analysis_job_id is not None:
            extra["analysis_job_id"] = str(analysis_job_id)
        extra["analysis_version"] = getattr(analysis, "analysis_version", None)
        if getattr(analysis, "analysis_version", None) == "dream_v1":
            try:
                from services.analysis.schema.dream_analysis_v1 import DreamAnalysisV1

                canonical = DreamAnalysisV1.model_validate(analysis.analysis_json or {})
                extra["dream_analysis_success"] = True
                extra["symbols_count"] = len(canonical.symbols)
                extra["archetypes_detected"] = len(canonical.jungian_interpretation.archetypes)
            except Exception:
                extra["dream_analysis_success"] = False
    logger.info(
        "Analysis runtime job %s",
        outcome,
        extra=extra,
    )
