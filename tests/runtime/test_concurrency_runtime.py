# stdlib
import asyncio
import random
from datetime import timedelta
from uuid import UUID

# thirdparty
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

# project
from db.models.analysis_job_model import AnalysisJob
from db.models.session_model import DreamSession
from services.analysis_policy import utc_now
from services.runtime.analysis_job_service import acquire_available_jobs, create_job, get_job
from services.runtime.analysis_runtime_executor import execute_analysis_job
from services.runtime.analysis_runtime_worker import AnalysisRuntimeWorker
from services.runtime.runtime_types import AnalysisJobStatus, RetryableAnalysisError
from tests.runtime.conftest import (
    ExecutionTracker,
    assert_all_jobs_terminal,
    assert_no_duplicate_active_execution,
    load_jobs,
    make_tracking_executor,
    seed_analysis_ready_session,
    seed_queued_jobs,
)

pytestmark = pytest.mark.integration

JOB_COUNT_RACE = 20
JOB_COUNT_STRESS = 40
STRESS_WORKERS = 3


async def _run_workers_until_drained(
    session_factory,
    workers: list[AnalysisRuntimeWorker],
    job_ids: list[UUID],
    *,
    max_rounds: int = 200,
) -> None:
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
async def test_dual_worker_race_each_job_executed_once(db_engine, user_id, execution_tracker):
    session_factory = sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    _, job_ids = await seed_queued_jobs(session_factory, user_id, JOB_COUNT_RACE)

    executor = make_tracking_executor(execution_tracker, delay_seconds=0.01)

    worker_a = AnalysisRuntimeWorker(
        session_factory=session_factory,
        worker_id="worker-a",
        batch_size=10,
        max_concurrency=5,
        poll_interval_seconds=0.01,
        executor=executor,
    )
    worker_b = AnalysisRuntimeWorker(
        session_factory=session_factory,
        worker_id="worker-b",
        batch_size=10,
        max_concurrency=5,
        poll_interval_seconds=0.01,
        executor=executor,
    )

    for _ in range(15):
        await asyncio.gather(worker_a.run_once(), worker_b.run_once())
        jobs = await load_jobs(session_factory, job_ids)
        if all(j.status in {AnalysisJobStatus.COMPLETED.value, AnalysisJobStatus.FAILED.value} for j in jobs):
            break

    await assert_all_jobs_terminal(session_factory, job_ids)
    assert_no_duplicate_active_execution(execution_tracker, job_ids)
    execution_tracker.assert_single_provider_call_per_job(job_ids)


@pytest.mark.asyncio
async def test_single_job_double_acquire_prevention_with_delayed_commit(db_engine, user_id):
    session_factory = sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory.begin() as setup:
        session = DreamSession(user_id=user_id, status="active")
        setup.add(session)
        await setup.flush()
        job = await create_job(
            setup,
            session_id=session.id,
            provider="mock",
            model="mock-v1",
            max_attempts=2,
        )
        job_id = job.id

    holder_ready = asyncio.Event()
    holder_may_commit = asyncio.Event()
    second_result: list = []

    async def holder_acquire_and_hold():
        session = session_factory()
        tx = await session.begin()
        try:
            acquired = await acquire_available_jobs(session, limit=1, locked_by="worker-a")
            assert [j.id for j in acquired] == [job_id]
            holder_ready.set()
            await holder_may_commit.wait()
            await tx.commit()
        finally:
            await session.close()

    async def challenger_acquire():
        await holder_ready.wait()
        session = session_factory()
        tx = await session.begin()
        try:
            acquired = await acquire_available_jobs(session, limit=1, locked_by="worker-b")
            second_result.extend(acquired)
            await tx.commit()
        finally:
            await session.close()

    holder_task = asyncio.create_task(holder_acquire_and_hold())
    challenger_task = asyncio.create_task(challenger_acquire())
    await holder_ready.wait()
    await asyncio.sleep(0.05)
    await challenger_task
    assert second_result == []
    holder_may_commit.set()
    await holder_task

    async with session_factory() as db:
        loaded = await db.scalar(select(AnalysisJob).where(AnalysisJob.id == job_id))
        assert loaded.status == AnalysisJobStatus.RUNNING.value
        assert loaded.locked_by == "worker-a"


@pytest.mark.asyncio
async def test_batch_contention_stress_lite(db_engine, user_id, execution_tracker):
    session_factory = sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    _, job_ids = await seed_queued_jobs(session_factory, user_id, JOB_COUNT_STRESS)

    async def _variable_delay_executor(db, job):
        delay = random.uniform(0.001, 0.02)
        return await make_tracking_executor(execution_tracker, delay_seconds=delay)(db, job)

    workers = [
        AnalysisRuntimeWorker(
            session_factory=session_factory,
            worker_id=f"worker-{i}",
            batch_size=15,
            max_concurrency=4,
            poll_interval_seconds=0.01,
            executor=_variable_delay_executor,
        )
        for i in range(STRESS_WORKERS)
    ]

    await _run_workers_until_drained(session_factory, workers, job_ids)

    await assert_all_jobs_terminal(session_factory, job_ids)
    assert_no_duplicate_active_execution(execution_tracker, job_ids)
    assert sum(execution_tracker.execution_counts[jid] for jid in job_ids) == len(job_ids)


@pytest.mark.asyncio
async def test_crash_during_execution_second_worker_does_not_parallel_execute(
    db_engine, user_id, execution_tracker
):
    session_factory = sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    _, job_ids = await seed_queued_jobs(session_factory, user_id, 1)
    job_id = job_ids[0]
    crash_after_start = asyncio.Event()

    async def _crash_executor(db, job):
        await execution_tracker.record_execution_start(job.id)
        await execution_tracker.record_provider_call(job.id)
        crash_after_start.set()
        raise RuntimeError("simulated worker crash before completion")

    worker_a = AnalysisRuntimeWorker(
        session_factory=session_factory,
        worker_id="worker-a",
        batch_size=1,
        max_concurrency=1,
        poll_interval_seconds=0.01,
        executor=_crash_executor,
    )
    worker_b = AnalysisRuntimeWorker(
        session_factory=session_factory,
        worker_id="worker-b",
        batch_size=1,
        max_concurrency=1,
        poll_interval_seconds=0.01,
        executor=make_tracking_executor(execution_tracker),
    )

    await worker_a.run_once()
    assert crash_after_start.is_set()
    assert execution_tracker.execution_counts[job_id] == 1

    await worker_b.run_once()

    assert execution_tracker.execution_counts[job_id] == 1
    jobs = await load_jobs(session_factory, [job_id])
    assert jobs[0].status == AnalysisJobStatus.RUNNING.value
    assert jobs[0].locked_by == "worker-a"


@pytest.mark.asyncio
async def test_no_duplicate_provider_call_under_worker_contention(db_engine, user_id, execution_tracker):
    session_factory = sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    _, job_ids = await seed_queued_jobs(session_factory, user_id, 15)

    executor = make_tracking_executor(execution_tracker, delay_seconds=0.005, provider_calls=True)
    workers = [
        AnalysisRuntimeWorker(
            session_factory=session_factory,
            worker_id=f"worker-{i}",
            batch_size=8,
            max_concurrency=4,
            poll_interval_seconds=0.01,
            executor=executor,
        )
        for i in range(2)
    ]

    await _run_workers_until_drained(session_factory, workers, job_ids)
    execution_tracker.assert_single_provider_call_per_job(job_ids)


@pytest.mark.asyncio
async def test_retry_isolation_only_one_worker_reprocesses_requeued_job(db_engine, user_id, execution_tracker):
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
    retry_done = asyncio.Event()

    async def _retry_once_orchestrator(db, session_id_arg, **kwargs):
        attempt_counter["n"] += 1
        if attempt_counter["n"] == 1:
            raise RetryableAnalysisError("transient")
        retry_done.set()

        class _StubAnalysis:
            thread_id = None

        return _StubAnalysis()

    async def _executor(db, job):
        await execution_tracker.record_execution_start(job.id)
        await execution_tracker.record_provider_call(job.id)
        result = await execute_analysis_job(db, job, orchestrator=_retry_once_orchestrator)
        await execution_tracker.record_execution_end(job.id)
        return result

    worker_a = AnalysisRuntimeWorker(
        session_factory=session_factory,
        worker_id="worker-a",
        batch_size=1,
        max_concurrency=1,
        poll_interval_seconds=0.01,
        executor=_executor,
    )
    worker_b = AnalysisRuntimeWorker(
        session_factory=session_factory,
        worker_id="worker-b",
        batch_size=1,
        max_concurrency=1,
        poll_interval_seconds=0.01,
        executor=_executor,
    )

    await worker_a.run_once()
    assert execution_tracker.execution_counts[job_id] == 1

    async with session_factory() as db:
        job = await get_job(db, job_id)
        assert job.status == AnalysisJobStatus.QUEUED.value
        job.available_after = utc_now().replace(tzinfo=None) - timedelta(seconds=1)
        await db.commit()

    for _ in range(10):
        await asyncio.gather(worker_a.run_once(), worker_b.run_once())
        async with session_factory() as db:
            job = await get_job(db, job_id)
            if job.status == AnalysisJobStatus.COMPLETED.value:
                break

    assert retry_done.is_set()
    assert execution_tracker.execution_counts[job_id] == 2
    execution_tracker.assert_no_overlapping_windows([job_id])

    windows = execution_tracker.active_windows[job_id]
    closed = [(s, e) for s, e in windows if e is not None]
    assert len(closed) == 2
    assert closed[0][1] <= closed[1][0] or closed[1][1] <= closed[0][0]
