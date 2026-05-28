# stdlib
from datetime import timedelta

# thirdparty
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

# project
from db.models.analysis_job_model import AnalysisJob
from db.models.session_model import DreamSession
from services.analysis_policy import utc_now
from services.runtime.analysis_job_service import (
    acquire_available_jobs,
    create_job,
    mark_completed,
    mark_failed,
    requeue,
)
from services.runtime.runtime_types import AnalysisJobStatus, InvalidJobTransitionError

pytestmark = pytest.mark.integration


async def _session(db_session: AsyncSession, user_id: int) -> DreamSession:
    session = DreamSession(user_id=user_id, status="active")
    db_session.add(session)
    await db_session.flush()
    return session


async def test_create_job_defaults_to_queued_and_available_now(db_session, user_id):
    session = await _session(db_session, user_id)

    job = await create_job(
        db_session,
        session_id=session.id,
        provider="mock",
        model="mock-v1",
        max_attempts=3,
    )

    assert job.status == AnalysisJobStatus.QUEUED.value
    assert job.attempts == 0
    assert job.max_attempts == 3
    assert job.available_after == job.created_at
    assert job.session_id == session.id


async def test_acquire_available_jobs_marks_running_atomically(db_session, user_id):
    session = await _session(db_session, user_id)
    job = await create_job(db_session, session_id=session.id, provider="mock", model="mock-v1", max_attempts=2)

    acquired = await acquire_available_jobs(db_session, limit=1, locked_by="worker-a")

    assert [item.id for item in acquired] == [job.id]
    assert acquired[0].status == AnalysisJobStatus.RUNNING.value
    assert acquired[0].attempts == 1
    assert acquired[0].locked_by == "worker-a"
    assert acquired[0].locked_at is not None
    assert acquired[0].started_at is not None


async def test_acquire_available_jobs_orders_by_available_after_created_at_and_id(db_session, user_id):
    session = await _session(db_session, user_id)
    first = await create_job(db_session, session_id=session.id, provider="mock", model="mock-v1", max_attempts=2)
    second = await create_job(db_session, session_id=session.id, provider="mock", model="mock-v1", max_attempts=2)
    third = await create_job(db_session, session_id=session.id, provider="mock", model="mock-v1", max_attempts=2)

    now = utc_now().replace(tzinfo=None)
    first.available_after = now + timedelta(seconds=20)
    second.available_after = now
    third.available_after = now + timedelta(seconds=10)
    await db_session.flush()

    acquired = await acquire_available_jobs(db_session, limit=3, locked_by="worker-a", now=now + timedelta(seconds=30))

    assert [job.id for job in acquired] == [second.id, third.id, first.id]


async def test_same_job_cannot_be_acquired_concurrently_by_two_workers(db_engine, user_id):
    session_factory = sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory.begin() as setup_session:
        session = DreamSession(user_id=user_id, status="active")
        setup_session.add(session)
        await setup_session.flush()
        job = await create_job(
            setup_session,
            session_id=session.id,
            provider="mock",
            model="mock-v1",
            max_attempts=2,
        )
        job_id = job.id

    first_session = session_factory()
    second_session = session_factory()
    first_tx = await first_session.begin()
    second_tx = await second_session.begin()
    try:
        first_acquired = await acquire_available_jobs(first_session, limit=1, locked_by="worker-a")
        second_acquired = await acquire_available_jobs(second_session, limit=1, locked_by="worker-b")

        assert [job.id for job in first_acquired] == [job_id]
        assert second_acquired == []
    finally:
        await second_tx.rollback()
        await first_tx.rollback()
        await second_session.close()
        await first_session.close()


async def test_requeue_uses_delayed_available_after(db_session, user_id):
    session = await _session(db_session, user_id)
    await create_job(db_session, session_id=session.id, provider="mock", model="mock-v1", max_attempts=3)
    acquired = await acquire_available_jobs(db_session, limit=1, locked_by="worker-a")
    retry_at = utc_now().replace(tzinfo=None) + timedelta(minutes=1)

    job = await requeue(
        db_session,
        acquired[0].id,
        available_after=retry_at,
        error_class="RetryableAnalysisError",
        error_message="transient",
    )

    assert job.status == AnalysisJobStatus.QUEUED.value
    assert job.available_after == retry_at
    assert job.retryable is True
    assert job.last_error_class == "RetryableAnalysisError"


async def test_terminal_failure_marks_failed(db_session, user_id):
    session = await _session(db_session, user_id)
    await create_job(db_session, session_id=session.id, provider="mock", model="mock-v1", max_attempts=1)
    acquired = await acquire_available_jobs(db_session, limit=1, locked_by="worker-a")

    job = await mark_failed(
        db_session,
        acquired[0].id,
        error_class="NonRetryableAnalysisError",
        error_message="schema violation",
        retryable=False,
    )

    assert job.status == AnalysisJobStatus.FAILED.value
    assert job.retryable is False
    assert job.completed_at is not None


async def test_cannot_complete_cancelled_job(db_session, user_id):
    session = await _session(db_session, user_id)
    job = await create_job(db_session, session_id=session.id, provider="mock", model="mock-v1", max_attempts=1)
    job.status = AnalysisJobStatus.CANCELLED.value
    await db_session.flush()

    with pytest.raises(InvalidJobTransitionError):
        await mark_completed(db_session, job.id, thread_id=None)


async def test_completed_job_cannot_be_acquired_again(db_session, user_id):
    session = await _session(db_session, user_id)
    await create_job(db_session, session_id=session.id, provider="mock", model="mock-v1", max_attempts=1)
    acquired = await acquire_available_jobs(db_session, limit=1, locked_by="worker-a")
    await mark_completed(db_session, acquired[0].id, thread_id=None)

    reacquired = await acquire_available_jobs(db_session, limit=1, locked_by="worker-b")
    loaded = await db_session.scalar(select(AnalysisJob).where(AnalysisJob.id == acquired[0].id))

    assert reacquired == []
    assert loaded.status == AnalysisJobStatus.COMPLETED.value
