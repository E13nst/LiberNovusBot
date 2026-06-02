# thirdparty
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

# project
from db.models.analysis_job_model import AnalysisJob
from db.models.dream_model import Dream
from db.models.session_analysis_model import SessionAnalysis
from services.dream_intake import register_incoming_dream
from services.runtime.analysis_job_service import acquire_available_jobs
from services.runtime.analysis_runtime_executor import execute_analysis_job
from services.runtime.analysis_runtime_worker import AnalysisRuntimeWorker
from services.runtime.runtime_types import AnalysisJobStatus
from tests.runtime.delivery_fakes import FakeRedis, RecordingTelegramDelivery

pytestmark = pytest.mark.integration


@pytest.fixture
def delivery_fakes():
    return FakeRedis(), RecordingTelegramDelivery()


async def test_dream_message_creates_analysis_job(db_session, user_id):
    result = await register_incoming_dream(db_session, telegram_id=user_id, text="I saw the sea")

    dream_count = await db_session.scalar(select(func.count()).select_from(Dream).where(Dream.user_id == user_id))
    job_count = await db_session.scalar(
        select(func.count()).select_from(AnalysisJob).where(AnalysisJob.session_id == result.dream.session_id)
    )

    assert dream_count == 1
    assert job_count == 1
    assert result.job.session_id == result.dream.session_id
    assert result.job.status == AnalysisJobStatus.QUEUED.value


async def test_each_accepted_dream_message_creates_one_job(db_session, user_id):
    first = await register_incoming_dream(db_session, telegram_id=user_id, text="dream one")
    second = await register_incoming_dream(db_session, telegram_id=user_id, text="dream two")
    third = await register_incoming_dream(db_session, telegram_id=user_id, text="dream three")

    dream_count = await db_session.scalar(select(func.count()).select_from(Dream).where(Dream.user_id == user_id))
    job_count = await db_session.scalar(
        select(func.count()).select_from(AnalysisJob).where(AnalysisJob.session_id == first.dream.session_id)
    )

    assert first.dream.session_id == second.dream.session_id == third.dream.session_id
    assert dream_count == 3
    assert job_count == 3
    assert len({first.job.id, second.job.id, third.job.id}) == 3


async def test_job_creation_failure_rolls_back_dream_save(db_session, user_id, monkeypatch):
    async def _fail_create_job(*args, **kwargs):
        raise RuntimeError("enqueue failed")

    monkeypatch.setattr("services.dream_intake.create_job", _fail_create_job)

    with pytest.raises(RuntimeError, match="enqueue failed"):
        await register_incoming_dream(db_session, telegram_id=user_id, text="should not persist")

    await db_session.rollback()

    dream_count = await db_session.scalar(select(func.count()).select_from(Dream).where(Dream.user_id == user_id))
    job_count = await db_session.scalar(select(func.count()).select_from(AnalysisJob))

    assert dream_count == 0
    assert job_count == 0


async def test_job_completion_triggers_delivery(db_session, user_id, delivery_fakes):
    redis, delivery = delivery_fakes
    await register_incoming_dream(db_session, telegram_id=user_id, text="river and bridge")
    acquired = await acquire_available_jobs(db_session, limit=1, locked_by="test-worker")
    assert len(acquired) == 1

    await execute_analysis_job(
        db_session,
        acquired[0],
        redis_client=redis,
        telegram_delivery=delivery,
    )

    assert len(delivery.calls) == 1


async def test_full_dream_pipeline_offline(db_engine, user_id, delivery_fakes):
    redis, delivery = delivery_fakes
    session_factory = sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory.begin() as db:
        intake = await register_incoming_dream(db, telegram_id=user_id, text="I crossed a bridge over dark water")
        session_id = intake.dream.session_id
        job_id = intake.job.id

    async def _executor(db, job):
        return await execute_analysis_job(
            db,
            job,
            redis_client=redis,
            telegram_delivery=delivery,
        )

    worker = AnalysisRuntimeWorker(
        session_factory=session_factory,
        worker_id="pipeline-worker",
        batch_size=1,
        max_concurrency=1,
        poll_interval_seconds=0.01,
        executor=_executor,
    )
    processed = await worker.run_once()

    assert processed == 1

    async with session_factory() as db:
        job_count = await db.scalar(
            select(func.count()).select_from(AnalysisJob).where(AnalysisJob.session_id == session_id)
        )
        analysis_count = await db.scalar(
            select(func.count()).select_from(SessionAnalysis).where(SessionAnalysis.session_id == session_id)
        )
        analysis = await db.scalar(
            select(SessionAnalysis)
            .where(SessionAnalysis.session_id == session_id)
            .order_by(SessionAnalysis.created_at.desc())
            .limit(1)
        )
        job = await db.get(AnalysisJob, job_id)

    assert job_count == 1
    assert analysis_count == 1
    assert job.status == AnalysisJobStatus.COMPLETED.value
    assert analysis is not None
    assert analysis.analysis_job_id == job.id
    assert len(delivery.calls) == 1
