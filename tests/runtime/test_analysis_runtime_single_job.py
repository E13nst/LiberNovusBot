# thirdparty
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

# project
from db.models.analysis_job_model import AnalysisJob
from db.models.dream_model import Dream
from db.models.session_model import DreamSession
from db.models.session_summary_model import SessionSummary
from services.runtime.analysis_job_service import create_job, get_job
from services.runtime.analysis_runtime_executor import execute_analysis_job
from services.runtime.analysis_runtime_worker import AnalysisRuntimeWorker
from services.runtime.runtime_types import AnalysisJobStatus

pytestmark = pytest.mark.integration


async def _analysis_ready_session(db: AsyncSession, user_id: int) -> DreamSession:
    session = DreamSession(user_id=user_id, status="active")
    db.add(session)
    await db.flush()
    db.add(
        SessionSummary(
            session_id=session.id,
            user_id=user_id,
            dream_count=1,
            key_symbols=["water"],
            recurring_words=[],
            raw_text_sample="river and bridge",
        )
    )
    db.add(
        Dream(user_id=user_id, text="I crossed a bridge over dark water", session_id=session.id)
    )
    await db.flush()
    return session


async def test_worker_does_not_reprocess_completed_job(db_engine, user_id):
    """Single-worker mode: completed jobs are not acquired on a second poll cycle."""
    session_factory = sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    orchestrator_calls = 0

    async def _counting_orchestrator(db, session_id, **kwargs):
        nonlocal orchestrator_calls
        orchestrator_calls += 1

        class _StubAnalysis:
            thread_id = None

        return _StubAnalysis()

    async with session_factory.begin() as db:
        session = await _analysis_ready_session(db, user_id)
        await create_job(
            db,
            session_id=session.id,
            provider="mock",
            model="mock-v1",
            max_attempts=1,
        )

    async def _executor(db, job):
        return await execute_analysis_job(db, job, orchestrator=_counting_orchestrator)

    worker = AnalysisRuntimeWorker(
        session_factory=session_factory,
        worker_id="worker-single",
        batch_size=1,
        max_concurrency=1,
        poll_interval_seconds=0.01,
        executor=_executor,
    )

    assert await worker.run_once() == 1
    assert orchestrator_calls == 1
    assert await worker.run_once() == 0
    assert orchestrator_calls == 1

    async with session_factory() as db:
        count = await db.scalar(select(func.count()).select_from(AnalysisJob))
        job = await db.scalar(select(AnalysisJob).limit(1))
        assert count == 1
        assert job is not None
        assert job.status == AnalysisJobStatus.COMPLETED.value
