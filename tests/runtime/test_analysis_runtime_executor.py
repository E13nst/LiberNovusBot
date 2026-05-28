# thirdparty
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# project
from db.models.dream_model import Dream
from db.models.session_model import DreamSession
from db.models.session_summary_model import SessionSummary
from services.runtime.analysis_job_service import acquire_available_jobs, create_job
from services.runtime.analysis_runtime_executor import execute_analysis_job
from services.runtime.runtime_types import (
    AnalysisJobStatus,
    NonRetryableAnalysisError,
    RetryableAnalysisError,
)

pytestmark = pytest.mark.integration


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


async def test_executor_completes_job_and_persists_analysis(db_session, user_id):
    session = await _analysis_ready_session(db_session, user_id)
    await create_job(db_session, session_id=session.id, provider="mock", model="mock-v1", max_attempts=1)
    acquired = await acquire_available_jobs(db_session, limit=1, locked_by="worker-a")

    job = await execute_analysis_job(db_session, acquired[0])

    assert job.status == AnalysisJobStatus.COMPLETED.value
    assert job.thread_id is not None
    assert job.completed_at is not None


async def test_executor_requeues_retryable_failure_with_available_after(db_session, user_id):
    session = await _analysis_ready_session(db_session, user_id)
    await create_job(db_session, session_id=session.id, provider="mock", model="mock-v1", max_attempts=2)
    acquired = await acquire_available_jobs(db_session, limit=1, locked_by="worker-a")

    async def _raise_retryable(*args, **kwargs):
        raise RetryableAnalysisError("provider unavailable")

    job = await execute_analysis_job(db_session, acquired[0], orchestrator=_raise_retryable)

    assert job.status == AnalysisJobStatus.QUEUED.value
    assert job.retryable is True
    assert job.available_after > job.created_at
    assert job.last_error_class == "RetryableAnalysisError"


async def test_executor_marks_retryable_failure_failed_after_max_attempts(db_session, user_id):
    session = await _analysis_ready_session(db_session, user_id)
    await create_job(db_session, session_id=session.id, provider="mock", model="mock-v1", max_attempts=1)
    acquired = await acquire_available_jobs(db_session, limit=1, locked_by="worker-a")

    async def _raise_retryable(*args, **kwargs):
        raise RetryableAnalysisError("provider unavailable")

    job = await execute_analysis_job(db_session, acquired[0], orchestrator=_raise_retryable)

    assert job.status == AnalysisJobStatus.FAILED.value
    assert job.retryable is True
    assert job.completed_at is not None


async def test_executor_marks_non_retryable_failure_failed(db_session, user_id):
    session = await _analysis_ready_session(db_session, user_id)
    await create_job(db_session, session_id=session.id, provider="mock", model="mock-v1", max_attempts=3)
    acquired = await acquire_available_jobs(db_session, limit=1, locked_by="worker-a")

    async def _raise_non_retryable(*args, **kwargs):
        raise NonRetryableAnalysisError("schema violation")

    job = await execute_analysis_job(db_session, acquired[0], orchestrator=_raise_non_retryable)

    assert job.status == AnalysisJobStatus.FAILED.value
    assert job.retryable is False
    assert job.last_error_class == "NonRetryableAnalysisError"


async def test_executor_treats_unclassified_exception_as_non_retryable(db_session, user_id):
    session = await _analysis_ready_session(db_session, user_id)
    await create_job(db_session, session_id=session.id, provider="mock", model="mock-v1", max_attempts=3)
    acquired = await acquire_available_jobs(db_session, limit=1, locked_by="worker-a")

    async def _raise_unknown(*args, **kwargs):
        raise RuntimeError("unexpected")

    job = await execute_analysis_job(db_session, acquired[0], orchestrator=_raise_unknown)

    assert job.status == AnalysisJobStatus.FAILED.value
    assert job.retryable is False
    assert job.last_error_class == "NonRetryableAnalysisError"


async def test_executor_does_not_call_domain_input_loader_directly(db_session, user_id, monkeypatch):
    session = await _analysis_ready_session(db_session, user_id)
    await create_job(db_session, session_id=session.id, provider="mock", model="mock-v1", max_attempts=1)
    acquired = await acquire_available_jobs(db_session, limit=1, locked_by="worker-a")
    called_with = {}

    async def _orchestrator(db, session_id, **kwargs):
        called_with["session_id"] = session_id

        class _Analysis:
            thread_id = None

        return _Analysis()

    async def _forbidden(*args, **kwargs):
        raise AssertionError("runtime must not call load_analysis_input")

    monkeypatch.setattr("services.analysis_input_service.load_analysis_input", _forbidden)

    job = await execute_analysis_job(db_session, acquired[0], orchestrator=_orchestrator)

    assert called_with["session_id"] == session.id
    assert job.status == AnalysisJobStatus.COMPLETED.value
