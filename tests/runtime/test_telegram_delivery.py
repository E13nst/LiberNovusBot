# stdlib
import asyncio
from uuid import UUID, uuid4

# thirdparty
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# project
from db.models.analysis_job_model import AnalysisJob
from db.models.dream_model import Dream
from db.models.session_analysis_model import SessionAnalysis
from db.models.session_model import DreamSession
from db.models.session_summary_model import SessionSummary
from services.analysis_policy import utc_now
from services.notifications.analysis_delivery_service import deliver_completed_analysis
from services.notifications.delivery_lock_service import acquire_delivery_lock
from services.runtime.analysis_job_service import acquire_available_jobs, create_job
from services.runtime.analysis_runtime_executor import execute_analysis_job
from tests.fixtures.dream_analysis_v1 import sample_dream_analysis_v1_json
from services.runtime.runtime_types import AnalysisJobStatus, RetryableAnalysisError
from tests.runtime.delivery_fakes import FakeRedis, RecordingTelegramDelivery

pytestmark = pytest.mark.integration

SAMPLE_ANALYSIS_JSON = sample_dream_analysis_v1_json()


async def _analysis_ready_session(db_session: AsyncSession, user_id: int) -> DreamSession:
    session = DreamSession(user_id=user_id, status="active")
    db_session.add(session)
    await db_session.flush()
    db_session.add(
        SessionSummary(
            session_id=session.id,
            user_id=user_id,
            dream_count=1,
            key_symbols=["water"],
            recurring_words=[],
            raw_text_sample="river and bridge",
        )
    )
    db_session.add(Dream(user_id=user_id, text="I crossed a bridge over dark water", session_id=session.id))
    await db_session.flush()
    return session


def _completed_job(job_id: UUID | None = None) -> AnalysisJob:
    job = AnalysisJob(
        session_id=uuid4(),
        status=AnalysisJobStatus.COMPLETED.value,
        provider="mock",
        model="mock-v1",
        mode="auto",
        attempts=1,
        max_attempts=1,
    )
    if job_id is not None:
        job.id = job_id
    return job


def _bound_analysis(*, job_id: UUID, user_id: int = 123456789) -> SessionAnalysis:
    return SessionAnalysis(
        session_id=uuid4(),
        thread_id=uuid4(),
        user_id=user_id,
        provider="mock",
        model="mock-v1",
        prompt_version="v1",
        analysis_version="dream_v1",
        analysis_json=SAMPLE_ANALYSIS_JSON,
        analysis_job_id=job_id,
    )


async def test_acquire_delivery_lock_is_idempotent_per_job_id():
    redis = FakeRedis()
    job_id = str(uuid4())

    assert await acquire_delivery_lock(redis, job_id) is True
    assert await acquire_delivery_lock(redis, job_id) is False


async def test_delivery_skipped_if_lock_exists():
    redis = FakeRedis()
    job_id = uuid4()
    await acquire_delivery_lock(redis, str(job_id))
    delivery = RecordingTelegramDelivery()
    job = _completed_job(job_id)
    analysis = _bound_analysis(job_id=job_id)

    delivered = await deliver_completed_analysis(job, analysis, redis_client=redis, telegram_delivery=delivery)

    assert delivered is False
    assert delivery.calls == []


async def test_no_duplicate_delivery_under_worker_race():
    redis = FakeRedis()
    job_id = uuid4()
    delivery = RecordingTelegramDelivery()
    job = _completed_job(job_id)
    analysis = _bound_analysis(job_id=job_id)

    results = await asyncio.gather(
        deliver_completed_analysis(job, analysis, redis_client=redis, telegram_delivery=delivery),
        deliver_completed_analysis(job, analysis, redis_client=redis, telegram_delivery=delivery),
    )

    assert sum(1 for result in results if result is True) == 1
    assert len(delivery.calls) == 1


async def test_failed_job_does_not_trigger_delivery(db_session, user_id):
    session = await _analysis_ready_session(db_session, user_id)
    await create_job(db_session, session_id=session.id, provider="mock", model="mock-v1", max_attempts=1)
    acquired = await acquire_available_jobs(db_session, limit=1, locked_by="worker-a")
    delivery = RecordingTelegramDelivery()
    redis = FakeRedis()

    async def _raise_retryable(*args, **kwargs):
        raise RetryableAnalysisError("transient")

    job = await execute_analysis_job(
        db_session,
        acquired[0],
        orchestrator=_raise_retryable,
        redis_client=redis,
        telegram_delivery=delivery,
    )

    assert job.status == AnalysisJobStatus.FAILED.value
    assert delivery.calls == []


async def test_delivery_failure_does_not_fail_job(db_session, user_id):
    session = await _analysis_ready_session(db_session, user_id)
    await create_job(db_session, session_id=session.id, provider="mock", model="mock-v1", max_attempts=1)
    acquired = await acquire_available_jobs(db_session, limit=1, locked_by="worker-a")
    delivery = RecordingTelegramDelivery(fail_on_call=1)
    redis = FakeRedis()

    job = await execute_analysis_job(
        db_session,
        acquired[0],
        redis_client=redis,
        telegram_delivery=delivery,
    )

    assert job.status == AnalysisJobStatus.COMPLETED.value
    assert len(delivery.calls) == 1


async def test_retry_same_job_no_double_delivery(db_session, user_id):
    session = await _analysis_ready_session(db_session, user_id)
    await create_job(
        db_session,
        session_id=session.id,
        provider="mock",
        model="mock-v1",
        max_attempts=3,
    )
    acquired = await acquire_available_jobs(db_session, limit=1, locked_by="worker-a")
    delivery = RecordingTelegramDelivery()
    redis = FakeRedis()
    attempt_counter = {"n": 0}

    async def _retry_once_orchestrator(db, session_id, **kwargs):
        attempt_counter["n"] += 1
        if attempt_counter["n"] == 1:
            raise RetryableAnalysisError("transient")

        from services.analysis_orchestrator import prepare_session_analysis
        from services.analysis_thread_service import build_session_analysis_row, persist_session_analysis_in_thread

        prepared = await prepare_session_analysis(db, session_id, mode=kwargs.get("mode", "auto"))
        analysis = await build_session_analysis_row(db, prepared)
        bound = analysis.with_job_id(acquired[0].id)
        return await persist_session_analysis_in_thread(db, prepared.thread, bound)

    first = await execute_analysis_job(
        db_session,
        acquired[0],
        orchestrator=_retry_once_orchestrator,
        redis_client=redis,
        telegram_delivery=delivery,
    )
    assert first.status == AnalysisJobStatus.QUEUED.value
    assert delivery.calls == []

    first.available_after = utc_now().replace(tzinfo=None)
    await db_session.flush()

    reacquired = await acquire_available_jobs(db_session, limit=1, locked_by="worker-b")
    second = await execute_analysis_job(
        db_session,
        reacquired[0],
        orchestrator=_retry_once_orchestrator,
        redis_client=redis,
        telegram_delivery=delivery,
    )

    assert second.status == AnalysisJobStatus.COMPLETED.value
    assert len(delivery.calls) == 1
