# stdlib
import asyncio
import uuid
from datetime import timedelta
from uuid import UUID

# thirdparty
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

# project
from db.models.session_analysis_model import SessionAnalysis
from services.analysis_policy import utc_now
from services.runtime.analysis_job_service import create_job, get_job
from services.runtime.analysis_runtime_worker import AnalysisRuntimeWorker
from services.runtime.runtime_types import AnalysisJobStatus, RetryableAnalysisError
from tests.runtime.conftest import (
    assert_all_jobs_terminal,
    load_jobs,
    seed_analysis_ready_session,
    seed_queued_jobs,
)

pytestmark = pytest.mark.integration

JOB_COUNT_CONCURRENT = 20


async def _load_session_analyses(session_factory, session_id: UUID) -> list[SessionAnalysis]:
    async with session_factory() as db:
        result = await db.execute(
            select(SessionAnalysis)
            .where(SessionAnalysis.session_id == session_id)
            .order_by(SessionAnalysis.created_at.asc())
        )
        return list(result.scalars().all())


async def _run_workers_until_drained(session_factory, workers, job_ids: list[UUID], *, max_rounds: int = 200) -> None:
    remaining = set(job_ids)
    for _ in range(max_rounds):
        if not remaining:
            break
        await asyncio.gather(*(worker.run_once() for worker in workers))
        jobs = await load_jobs(session_factory, list(remaining))
        terminal = {AnalysisJobStatus.COMPLETED.value, AnalysisJobStatus.FAILED.value}
        remaining = {job.id for job in jobs if job.status not in terminal}
    assert not remaining, f"jobs not drained: {remaining}"


@pytest.mark.asyncio
async def test_job_result_binding(db_engine, user_id):
    """Completed runtime analysis binds exactly one analysis row to its job id."""
    session_factory = sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    session_id = await seed_analysis_ready_session(session_factory, user_id)

    async with session_factory.begin() as db:
        job = await create_job(
            db,
            session_id=session_id,
            provider="mock",
            model="mock-v1",
            max_attempts=1,
        )
        job_id = job.id

    worker = AnalysisRuntimeWorker(
        session_factory=session_factory,
        worker_id="worker-binding",
        batch_size=1,
        max_concurrency=1,
        poll_interval_seconds=0.01,
    )
    assert await worker.run_once() == 1

    analyses = await _load_session_analyses(session_factory, session_id)
    assert len(analyses) == 1
    assert analyses[0].analysis_job_id == job_id


@pytest.mark.asyncio
async def test_retry_preserves_job_identity(db_engine, user_id, monkeypatch):
    """Runtime retry requeues the same job row; attempts increment without creating a new job."""
    session_factory = sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    session_id = await seed_analysis_ready_session(session_factory, user_id)

    async with session_factory.begin() as db:
        job = await create_job(
            db,
            session_id=session_id,
            provider="mock",
            model="mock-v1",
            max_attempts=3,
        )
        job_id = job.id

    attempt_counter = {"n": 0}
    from services.analysis_orchestrator import prepare_session_analysis as original_prepare

    async def _flaky_prepare(*args, **kwargs):
        attempt_counter["n"] += 1
        if attempt_counter["n"] == 1:
            raise RetryableAnalysisError("transient")
        return await original_prepare(*args, **kwargs)

    monkeypatch.setattr("services.runtime.analysis_runtime_executor.prepare_session_analysis", _flaky_prepare)

    worker = AnalysisRuntimeWorker(
        session_factory=session_factory,
        worker_id="worker-retry",
        batch_size=1,
        max_concurrency=1,
        poll_interval_seconds=0.01,
    )

    assert await worker.run_once() == 1
    async with session_factory() as db:
        job = await get_job(db, job_id)
        assert job.status == AnalysisJobStatus.QUEUED.value
        assert job.id == job_id
        assert job.attempts == 1
        job.available_after = utc_now().replace(tzinfo=None) - timedelta(seconds=1)
        await db.commit()

    assert await worker.run_once() == 1

    async with session_factory() as db:
        job = await get_job(db, job_id)
        assert job.id == job_id
        assert job.status == AnalysisJobStatus.COMPLETED.value
        assert job.attempts == 2


@pytest.mark.asyncio
async def test_reprocessing_same_job_does_not_create_second_analysis(db_engine, user_id):
    """A completed job is not re-acquired; no duplicate analysis row is created."""
    session_factory = sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    session_id = await seed_analysis_ready_session(session_factory, user_id)

    async with session_factory.begin() as db:
        job = await create_job(
            db,
            session_id=session_id,
            provider="mock",
            model="mock-v1",
            max_attempts=1,
        )
        job_id = job.id

    worker = AnalysisRuntimeWorker(
        session_factory=session_factory,
        worker_id="worker-idempotent",
        batch_size=1,
        max_concurrency=1,
        poll_interval_seconds=0.01,
    )

    assert await worker.run_once() == 1
    analyses_after_first = await _load_session_analyses(session_factory, session_id)
    assert len(analyses_after_first) == 1
    assert analyses_after_first[0].analysis_job_id == job_id

    assert await worker.run_once() == 0

    analyses_after_second = await _load_session_analyses(session_factory, session_id)
    assert len(analyses_after_second) == 1
    assert analyses_after_second[0].id == analyses_after_first[0].id
    assert analyses_after_second[0].analysis_job_id == job_id

    async with session_factory() as db:
        job = await get_job(db, job_id)
        assert job.status == AnalysisJobStatus.COMPLETED.value


async def _seed_analysis_ready_jobs(session_factory, user_id: int, count: int) -> tuple[list[UUID], list[UUID]]:
    session_ids: list[UUID] = []
    job_ids: list[UUID] = []
    for _ in range(count):
        session_id = await seed_analysis_ready_session(session_factory, user_id)
        _, created_job_ids = await seed_queued_jobs(
            session_factory,
            user_id,
            1,
            session_id=session_id,
            max_attempts=1,
        )
        session_ids.append(session_id)
        job_ids.extend(created_job_ids)
    return session_ids, job_ids


@pytest.mark.asyncio
async def test_concurrent_workers_no_cross_binding(db_engine, user_id):
    session_factory = sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    session_ids, job_ids = await _seed_analysis_ready_jobs(session_factory, user_id, JOB_COUNT_CONCURRENT)

    workers = [
        AnalysisRuntimeWorker(
            session_factory=session_factory,
            worker_id=f"worker-{i}",
            batch_size=10,
            max_concurrency=5,
            poll_interval_seconds=0.01,
        )
        for i in range(2)
    ]
    await _run_workers_until_drained(session_factory, workers, job_ids)
    await assert_all_jobs_terminal(session_factory, job_ids)

    analyses: list[SessionAnalysis] = []
    for session_id in session_ids:
        analyses.extend(await _load_session_analyses(session_factory, session_id))
    completed_jobs = await load_jobs(session_factory, job_ids)
    completed_job_ids = {job.id for job in completed_jobs if job.status == AnalysisJobStatus.COMPLETED.value}

    bound_analyses = [analysis for analysis in analyses if analysis.analysis_job_id is not None]
    assert len(bound_analyses) == len(completed_job_ids)
    assert {analysis.analysis_job_id for analysis in bound_analyses} == completed_job_ids
    assert len({analysis.analysis_job_id for analysis in bound_analyses}) == len(bound_analyses)


def test_analysis_job_id_write_once():
    """with_job_id returns a new bound row and refuses cross-job rebinding."""
    bound_job_id = uuid.uuid4()
    analysis = SessionAnalysis(
        id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        thread_id=uuid.uuid4(),
        user_id=1,
        provider="mock",
        model="mock-v1",
        prompt_version="v1",
        analysis_version="v1",
        analysis_json={"summary": "test"},
    )
    bound = analysis.with_job_id(bound_job_id)
    assert bound is not analysis
    assert bound.analysis_job_id == bound_job_id
    assert analysis.analysis_job_id is None

    rebound = bound.with_job_id(bound_job_id)
    assert rebound is bound

    with pytest.raises(ValueError):
        bound.with_job_id(uuid.uuid4())
