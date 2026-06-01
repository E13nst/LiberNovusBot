# stdlib
import logging
from uuid import UUID

# thirdparty
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

# project
from db.models.analysis_job_model import AnalysisJob
from db.models.session_analysis_model import SessionAnalysis
from services.analysis_contract import validate_analysis_output
from services.response_parser import extract_json, parse_json
from services.runtime.analysis_job_service import create_job, get_job
from services.runtime.analysis_runtime_executor import execute_analysis_job
from services.runtime.analysis_runtime_worker import AnalysisRuntimeWorker
from services.runtime.runtime_types import AnalysisJobStatus
from services.session_analysis_service import get_session_analysis
from tests.smoke.conftest import seed_smoke_session

pytestmark = pytest.mark.integration


def _log_has_fields(record, **fields) -> bool:
    for key, expected in fields.items():
        if getattr(record, key, None) != expected:
            return False
    return True


@pytest.mark.openai_smoke
async def test_runtime_openai_job_lifecycle_persists_analysis(
    db_engine,
    user_id,
    openai_smoke_provider,
    openai_smoke_runtime_config,
    caplog,
):
    """POST path equivalent: job queued -> worker running -> OpenAI -> persist -> completed."""
    session_factory = sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    session_id: UUID
    job_id: UUID

    async with session_factory.begin() as db:
        session = await seed_smoke_session(db, user_id)
        session_id = session.id
        job = await create_job(
            db,
            session_id=session_id,
            provider="openai",
            model=openai_smoke_runtime_config.default_model,
            max_attempts=1,
        )
        job_id = job.id
        assert job.status == AnalysisJobStatus.QUEUED.value

    running_observed = False

    async def _runtime_executor(db: AsyncSession, job: AnalysisJob) -> AnalysisJob:
        nonlocal running_observed
        current = await get_job(db, job.id)
        assert current is not None
        assert current.status == AnalysisJobStatus.RUNNING.value
        running_observed = True
        return await execute_analysis_job(db, job)

    worker = AnalysisRuntimeWorker(
        session_factory=session_factory,
        worker_id="openai-smoke-worker",
        batch_size=1,
        max_concurrency=1,
        poll_interval_seconds=0.01,
        executor=_runtime_executor,
    )

    with caplog.at_level(logging.INFO):
        processed = await worker.run_once()

    assert processed == 1
    assert running_observed
    assert openai_smoke_provider.call_count == 1

    raw = openai_smoke_provider.last_response
    assert raw is not None
    assert raw.raw_text.strip()
    validate_analysis_output(parse_json(extract_json(raw.raw_text)))

    async with session_factory() as db:
        job = await get_job(db, job_id)
        assert job is not None
        assert job.status == AnalysisJobStatus.COMPLETED.value
        assert job.thread_id is not None
        assert job.completed_at is not None
        assert job.attempts == 1
        assert job.retryable is False

        analysis = await get_session_analysis(db, session_id)
        assert analysis is not None
        assert analysis.thread_id == job.thread_id
        assert analysis.provider == "openai"
        assert analysis.model == openai_smoke_runtime_config.default_model
        validate_analysis_output(analysis.analysis_json)

        analysis_count = await db.scalar(
            select(func.count())
            .select_from(SessionAnalysis)
            .where(SessionAnalysis.session_id == session_id)
        )
        assert analysis_count == 1

    assert any(
        record.message == "Analysis runtime executing job"
        and _log_has_fields(
            record,
            job_id=str(job_id),
            session_id=str(session_id),
            provider="openai",
        )
        for record in caplog.records
    )
    assert any(
        record.message.startswith("Analysis runtime job ")
        and getattr(record, "outcome", None) == "completed"
        and getattr(record, "job_id", None) == str(job_id)
        for record in caplog.records
    )
    assert any(
        record.message == "LLM response parsed"
        and getattr(record, "parse_success", None) is True
        and getattr(record, "session_id", None) == str(session_id)
        for record in caplog.records
    )
    assert any(
        record.message == "LLM analysis contract validated"
        and getattr(record, "contract_success", None) is True
        and getattr(record, "session_id", None) == str(session_id)
        for record in caplog.records
    )

    with caplog.at_level(logging.INFO):
        second_pass = await worker.run_once()

    assert second_pass == 0
    assert openai_smoke_provider.call_count == 1
