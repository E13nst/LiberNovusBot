import uuid
from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

import settings
from db.db_setup import get_session
from db.models.admin_prompt_version_model import AdminPromptVersion
from routers.admin import admin_router
from services.admin.prompt_version_service import create_prompt_version, list_prompt_versions
from services.runtime.dialogue_router_service import process_incoming_message

pytestmark = pytest.mark.integration


@pytest.fixture
def admin_token(monkeypatch) -> str:
    token = "test-admin-token"
    monkeypatch.setattr(settings, "ADMIN_TOKEN", token)
    return token


@pytest.fixture
async def admin_client(db_engine, monkeypatch, admin_token):
    monkeypatch.setattr("services.config.runtime_guards._kill_switch_env_mode", "local")
    session_factory = sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory.begin() as session:
            yield session

    app = FastAPI(title="admin-test-api")
    app.include_router(admin_router)
    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def test_admin_api_requires_x_admin_token(admin_client):
    assert (await admin_client.get("/admin/api/sessions")).status_code == 401
    assert (
        await admin_client.get(
            "/admin/api/sessions",
            headers={"X-Admin-Token": "wrong"},
        )
    ).status_code == 403


async def test_admin_sessions_slice_projects_events_policy_trace_and_dreams(
    admin_client,
    db_engine,
    admin_token,
    user_id,
):
    response = await admin_client.post(
        "/dreams-not-mounted",
        headers={"X-Admin-Token": admin_token},
    )
    assert response.status_code == 404

    session_factory = sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory.begin() as db:
        route_result = await process_incoming_message(
            db,
            telegram_id=user_id,
            text="Мне снился океан и большая светлая башня у берега.",
        )
        assert route_result.intake_result is not None
        session_id = route_result.intake_result.dream.session_id
        dream_id = route_result.intake_result.dream.id

    headers = {"X-Admin-Token": admin_token}
    sessions = (await admin_client.get("/admin/api/sessions", headers=headers)).json()
    assert sessions["sessions"][0]["id"] == str(session_id)
    assert sessions["sessions"][0]["dream_count"] == 1
    assert sessions["sessions"][0]["job_count"] == 1

    detail = (await admin_client.get(f"/admin/api/sessions/{session_id}", headers=headers)).json()
    assert detail["id"] == str(session_id)
    assert detail["user_id"] == user_id

    dreams = (await admin_client.get(f"/admin/api/sessions/{session_id}/dreams", headers=headers)).json()
    assert dreams["dreams"][0]["id"] == dream_id
    assert "светлая башня" in dreams["dreams"][0]["text"]

    policy = (await admin_client.get(f"/admin/api/sessions/{session_id}/policy", headers=headers)).json()
    assert policy["policy_traces"][0]["decision"]["route"] == "ROUTE_REFLECTION"
    assert policy["policy_traces"][0]["outcome"]["dream_id"] == dream_id

    events = (await admin_client.get(f"/admin/api/sessions/{session_id}/events", headers=headers)).json()
    assert [event["type"] for event in events["events"]][:3] == [
        "INPUT",
        "POLICY",
        "DREAM_CREATED",
    ]
    assert events["events"][0]["session_id"] == str(session_id)

    trace = (await admin_client.get(f"/admin/api/sessions/{session_id}/trace", headers=headers)).json()
    alias = (await admin_client.get(f"/admin/api/sessions/{session_id}/policy-trace", headers=headers)).json()
    assert trace == alias
    assert trace["timeline"][0]["type"] == "INPUT"

    dream = (await admin_client.get(f"/admin/api/dreams/{dream_id}", headers=headers)).json()
    assert dream["id"] == dream_id
    assert dream["session_id"] == str(session_id)


async def test_admin_prompt_versions_are_insert_only_and_active_is_consistent(
    admin_client,
    db_engine,
    admin_token,
):
    session_factory = sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory.begin() as db:
        first = await create_prompt_version(
            db,
            prompt_type="reflection",
            content="first prompt",
            active=True,
        )

    headers = {"X-Admin-Token": admin_token}
    response = await admin_client.post(
        f"/admin/api/prompts/{first.id}",
        headers=headers,
        json={"content": "second prompt"},
    )

    assert response.status_code == 200
    created = response.json()
    assert created["prompt_type"] == "reflection"
    assert created["version"] == 2
    assert created["active_flag"] is True

    async with session_factory() as db:
        versions = await list_prompt_versions(db)
        rows = (await db.execute(select(AdminPromptVersion))).scalars().all()

    assert [version.version for version in versions] == [2, 1]
    assert sum(1 for row in rows if row.active_flag) == 1
    assert str(first.id) != created["id"]


async def test_admin_returns_404_for_missing_entities(admin_client, admin_token):
    headers = {"X-Admin-Token": admin_token}

    assert (await admin_client.get(f"/admin/api/sessions/{uuid.uuid4()}", headers=headers)).status_code == 404
    assert (await admin_client.get("/admin/api/dreams/999999", headers=headers)).status_code == 404
