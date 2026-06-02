# stdlib
from collections.abc import AsyncGenerator

# thirdparty
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

# project
from tests.support.test_app import build_test_api


@pytest_asyncio.fixture
async def api_client(db_engine, monkeypatch):
    """In-process ASGI client; temporarily allow httpx for loopback transport only."""
    monkeypatch.setattr("services.config.runtime_guards._kill_switch_env_mode", "local")
    session_factory = sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory.begin() as session:
            yield session

    test_app = build_test_api(override_get_session)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
