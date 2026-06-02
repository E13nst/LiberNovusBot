# stdlib
import logging
from collections.abc import AsyncGenerator
from uuid import UUID

# thirdparty
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

# project
from db.models.analysis_job_model import AnalysisJob
from db.models.dream_model import Dream
from db.models.session_analysis_model import SessionAnalysis
from services.analysis_contract import validate_analysis_output
from services.runtime.analysis_job_service import get_job
from services.runtime.analysis_runtime_worker import AnalysisRuntimeWorker
from services.runtime.runtime_delivery_overrides import runtime_delivery_overrides
from services.runtime.runtime_types import AnalysisJobStatus
from services.session_analysis_service import get_session_analysis
from tests.integration.test_telegram_webhook_intake import E2E_DREAM_TEXT
from tests.runtime.delivery_fakes import FakeRedis, RecordingTelegramDelivery
from tests.support.test_app import build_test_api
from tests.support.telegram_updates import make_telegram_update

pytestmark = pytest.mark.integration


def _record_has_fields(record: logging.LogRecord, **fields) -> bool:
    for key, expected in fields.items():
        if getattr(record, key, None) != expected:
            return False
    return True


@pytest.mark.openai_e2e
async def test_real_openai_dream_e2e_via_telegram_webhook(
    db_engine,
    user_id,
    openai_e2e_provider,
    openai_e2e_runtime_config,
    caplog,
):
    """Webhook intake -> worker -> real OpenAI -> contract -> persistence -> fake delivery."""
    session_factory = sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    redis = FakeRedis()
    delivery = RecordingTelegramDelivery()

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory.begin() as session:
            yield session

    test_app = build_test_api(override_get_session)
    transport = ASGITransport(app=test_app)

    session_id: UUID
    job_id: UUID
    analysis_id: UUID

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/telegram/webhook",
            json=make_telegram_update(text=E2E_DREAM_TEXT, user_id=user_id),
        )
        assert response.status_code == 200

    async with session_factory() as db:
        dream_count = await db.scalar(select(func.count()).select_from(Dream).where(Dream.user_id == user_id))
        job_count = await db.scalar(select(func.count()).select_from(AnalysisJob))
        job = await db.scalar(select(AnalysisJob).limit(1))
        assert dream_count == 1
        assert job_count == 1
        assert job is not None
        assert job.status == AnalysisJobStatus.QUEUED.value
        session_id = job.session_id
        job_id = job.id

    worker = AnalysisRuntimeWorker(
        session_factory=session_factory,
        worker_id="openai-e2e-worker",
        batch_size=1,
        max_concurrency=1,
        poll_interval_seconds=0.01,
    )

    with caplog.at_level(logging.INFO), runtime_delivery_overrides(
        redis_client=redis,
        telegram_delivery=delivery,
    ):
        processed = await worker.run_once()

    assert processed == 1
    assert openai_e2e_provider.call_count == 1

    async with session_factory() as db:
        job = await get_job(db, job_id)
        assert job is not None, (
            f"expected completed job, got status={job.status} "
            f"error={job.last_error_class}: {job.last_error_message}"
        )
        assert job.status == AnalysisJobStatus.COMPLETED.value
        assert job.attempts == 1

        analysis = await get_session_analysis(db, session_id)
        assert analysis is not None
        assert analysis.provider == "openai"
        assert analysis.model == openai_e2e_runtime_config.default_model
        assert analysis.analysis_job_id == job.id
        validate_analysis_output(analysis.analysis_json)
        analysis_id = analysis.id

        analysis_count = await db.scalar(
            select(func.count())
            .select_from(SessionAnalysis)
            .where(SessionAnalysis.session_id == session_id)
        )
        assert analysis_count == 1

    assert len(delivery.calls) == 1
    delivered_chat_id, delivered_analysis = delivery.calls[0]
    assert delivered_chat_id == str(user_id)
    assert delivered_analysis.id == analysis_id

    assert any(
        _record_has_fields(
            record,
            job_id=str(job_id),
            session_id=str(session_id),
            provider="openai",
            model=openai_e2e_runtime_config.default_model,
        )
        for record in caplog.records
        if record.name == "services.runtime.analysis_runtime_executor"
    )
    assert any(
        getattr(record, "analysis_id", None) is not None
        and getattr(record, "outcome", None) == "completed"
        and getattr(record, "job_id", None) == str(job_id)
        for record in caplog.records
        if record.name == "services.runtime.analysis_runtime_executor"
    )
    assert any(
        _record_has_fields(record, session_id=str(session_id), parse_success=True)
        for record in caplog.records
        if record.name == "services.analysis_orchestrator"
    )
    assert any(
        _record_has_fields(record, session_id=str(session_id), contract_success=True)
        for record in caplog.records
        if record.name == "services.analysis_orchestrator"
    )

    with caplog.at_level(logging.INFO), runtime_delivery_overrides(
        redis_client=redis,
        telegram_delivery=delivery,
    ):
        second_pass = await worker.run_once()

    assert second_pass == 0
    assert openai_e2e_provider.call_count == 1
    assert len(delivery.calls) == 1


def test_openai_e2e_skipped_without_opt_in(monkeypatch):
    """Default pytest runs must not call OpenAI E2E."""
    monkeypatch.delenv("RUN_OPENAI_E2E", raising=False)
    monkeypatch.setenv("ENV_MODE", "test")
    monkeypatch.setenv("LLM_PROVIDER", "mock")

    from tests.smoke.conftest import openai_e2e_skip_reason

    assert openai_e2e_skip_reason() is not None
