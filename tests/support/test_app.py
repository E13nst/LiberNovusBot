# stdlib
from collections.abc import AsyncGenerator, Callable

# thirdparty
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

# project
from db.db_setup import get_session
from routers.telegram_webhook import telegram_webhook_router


def build_test_api(session_dependency: Callable[..., AsyncGenerator[AsyncSession, None]]) -> FastAPI:
    """Minimal FastAPI app for in-process webhook tests (no runtime worker startup)."""
    test_app = FastAPI(title="test-api")
    test_app.include_router(telegram_webhook_router, prefix="/telegram")
    test_app.dependency_overrides[get_session] = session_dependency
    return test_app
