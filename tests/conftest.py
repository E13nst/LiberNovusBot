# stdlib
import os

os.environ["ENV_MODE"] = "test"
os.environ.setdefault("LLM_PROVIDER", "openai")
os.environ.setdefault("ANALYSIS_RUNTIME_ENABLED", "true")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-should-be-ignored")

# thirdparty
import pytest
import pytest_asyncio
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:password@localhost:5433/mini_app_db_test",
)

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["DATABASE_URL_PSYCOPG2"] = TEST_DATABASE_URL.replace("+asyncpg", "+psycopg2")

# project
from db import models  # noqa: E402,F401
from db.db_setup import Base  # noqa: E402


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncSession:
    async with db_engine.connect() as connection:
        transaction = await connection.begin()
        session_factory = sessionmaker(bind=connection, class_=AsyncSession, expire_on_commit=False)

        session = session_factory()
        try:
            yield session
        finally:
            await session.close()
            if transaction.is_active:
                await transaction.rollback()


@pytest.fixture
def user_id() -> int:
    return 123456789
