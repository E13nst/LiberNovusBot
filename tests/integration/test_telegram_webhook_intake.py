# thirdparty
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

# project
from db.models.analysis_job_model import AnalysisJob
from db.models.dream_model import Dream
from services.runtime.runtime_types import AnalysisJobStatus
from tests.support.telegram_updates import make_telegram_update

pytestmark = pytest.mark.integration

E2E_DREAM_TEXT = "Мне снился океан и разрушенный город"


async def test_telegram_webhook_creates_dream_and_queued_job(api_client, db_engine, user_id):
    response = await api_client.post(
        "/telegram/webhook",
        json=make_telegram_update(text=E2E_DREAM_TEXT, user_id=user_id),
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}

    session_factory = sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        dream_count = await db.scalar(select(func.count()).select_from(Dream).where(Dream.user_id == user_id))
        job_count = await db.scalar(select(func.count()).select_from(AnalysisJob))
        job = await db.scalar(select(AnalysisJob).limit(1))

    assert dream_count == 1
    assert job_count == 1
    assert job is not None
    assert job.status == AnalysisJobStatus.QUEUED.value


async def test_telegram_webhook_short_unclear_message_routes_to_clarification_without_enqueue(
    api_client,
    db_engine,
    user_id,
):
    response = await api_client.post(
        "/telegram/webhook",
        json=make_telegram_update(text="вода", user_id=user_id),
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}

    session_factory = sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        dream_count = await db.scalar(select(func.count()).select_from(Dream).where(Dream.user_id == user_id))
        job_count = await db.scalar(select(func.count()).select_from(AnalysisJob))

    assert dream_count == 0
    assert job_count == 0
