# thirdparty
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

# project
from db.models.analysis_job_model import AnalysisJob
from db.models.session_model import DreamSession
from services.runtime.analysis_job_service import create_job, mark_completed
from services.runtime.analysis_runtime_worker import AnalysisRuntimeWorker
from services.runtime.runtime_types import AnalysisJobStatus

pytestmark = pytest.mark.integration


async def _seed_jobs(session_factory, user_id: int, count: int) -> list:
    async with session_factory.begin() as db:
        session = DreamSession(user_id=user_id, status="active")
        db.add(session)
        await db.flush()
        jobs = []
        for _ in range(count):
            jobs.append(
                await create_job(
                    db,
                    session_id=session.id,
                    provider="mock",
                    model="mock-v1",
                    max_attempts=1,
                )
            )
        return [job.id for job in jobs]


async def test_worker_respects_batch_size(db_engine, user_id):
    session_factory = sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    await _seed_jobs(session_factory, user_id, count=3)
    executed = []

    async def _executor(db, job):
        executed.append(job.id)
        return await mark_completed(db, job.id, thread_id=None)

    worker = AnalysisRuntimeWorker(
        session_factory=session_factory,
        worker_id="worker-a",
        batch_size=2,
        max_concurrency=2,
        poll_interval_seconds=0.01,
        executor=_executor,
    )

    await worker.run_once()

    assert len(executed) == 2


async def test_worker_does_not_track_jobs_between_polling_cycles(db_engine, user_id):
    session_factory = sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    await _seed_jobs(session_factory, user_id, count=2)
    executed = []

    async def _executor(db, job):
        executed.append(job.id)
        return await mark_completed(db, job.id, thread_id=None)

    worker = AnalysisRuntimeWorker(
        session_factory=session_factory,
        worker_id="worker-a",
        batch_size=1,
        max_concurrency=1,
        poll_interval_seconds=0.01,
        executor=_executor,
    )

    await worker.run_once()
    await worker.run_once()

    assert len(executed) == 2
    assert len(set(executed)) == 2


async def test_worker_shutdown_stops_new_acquisition_but_does_not_force_fail_running_jobs(db_engine, user_id):
    session_factory = sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    job_ids = await _seed_jobs(session_factory, user_id, count=1)

    async def _executor(db, job):
        return job

    worker = AnalysisRuntimeWorker(
        session_factory=session_factory,
        worker_id="worker-a",
        batch_size=1,
        max_concurrency=1,
        poll_interval_seconds=0.01,
        executor=_executor,
    )

    await worker.stop()
    await worker.run_once()

    async with session_factory() as db:
        job = await db.scalar(select(AnalysisJob).where(AnalysisJob.id == job_ids[0]))

    assert job.status == AnalysisJobStatus.QUEUED.value
