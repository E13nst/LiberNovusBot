# stdlib
from collections.abc import AsyncGenerator

# thirdparty
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

# project
from db.db_setup import get_session
from routers.dreams import dreams_router
from routers.journal import journal_router
from services.ingress.ingress_service import process_incoming_message

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def journal_client(db_engine, monkeypatch):
    monkeypatch.setattr("services.config.runtime_guards._kill_switch_env_mode", "local")
    session_factory = sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory.begin() as session:
            yield session

    app = FastAPI()
    app.include_router(dreams_router, prefix="/dreams")
    app.include_router(journal_router, prefix="/api/v1")
    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_journal_lists_only_own_dreams(journal_client, db_engine, user_id):
    other_id = user_id + 1
    session_factory = sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory.begin() as db:
        await process_incoming_message(
            db,
            telegram_id=user_id,
            text="Мой сон про воду и мост в тумане утром",
        )
        await process_incoming_message(
            db,
            telegram_id=other_id,
            text="Чужой сон про лес и реку в ночи",
        )

    headers = {"X-Telegram-User-Id": str(user_id)}
    dreams = await journal_client.get("/api/v1/journal/dreams", headers=headers)
    assert dreams.status_code == 200
    payload = dreams.json()
    assert len(payload) == 1
    assert "вода" in payload[0]["excerpt"] or "мост" in payload[0]["excerpt"]
