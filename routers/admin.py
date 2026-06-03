from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from db.db_setup import get_session
from db.schemas.admin_schema import (
    AdminDreamListResponse,
    AdminDreamView,
    AdminEventListResponse,
    AdminGlobalDreamListResponse,
    AdminPolicyTraceListResponse,
    AdminPromptListResponse,
    AdminPromptUpdateRequest,
    AdminPromptVersionView,
    AdminSessionDetail,
    AdminSessionListResponse,
    AdminTraceResponse,
    AdminUserListResponse,
)
from services.admin.admin_console_service import (
    build_admin_events,
    build_admin_trace,
    get_admin_dream,
    get_admin_session,
    list_admin_all_dreams,
    list_admin_policy_traces,
    list_admin_session_dreams,
    list_admin_sessions,
    list_admin_users,
)
from services.admin.prompt_version_service import (
    create_next_prompt_version,
    list_prompt_versions,
)
from utils.admin_auth import require_admin_token

admin_router = APIRouter(
    prefix="/admin/api",
    tags=["Admin"],
    dependencies=[Depends(require_admin_token)],
)


@admin_router.get("/users", response_model=AdminUserListResponse)
async def list_admin_users_endpoint(db: AsyncSession = Depends(get_session)):
    return AdminUserListResponse(users=await list_admin_users(db))


@admin_router.get("/dreams", response_model=AdminGlobalDreamListResponse)
async def list_admin_dreams_endpoint(db: AsyncSession = Depends(get_session)):
    return AdminGlobalDreamListResponse(dreams=await list_admin_all_dreams(db))


@admin_router.get("/sessions", response_model=AdminSessionListResponse)
async def list_admin_sessions_endpoint(db: AsyncSession = Depends(get_session)):
    return AdminSessionListResponse(sessions=await list_admin_sessions(db))


@admin_router.get("/sessions/{session_id}", response_model=AdminSessionDetail)
async def get_admin_session_endpoint(
    session_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    session = await get_admin_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@admin_router.get("/sessions/{session_id}/events", response_model=AdminEventListResponse)
async def list_admin_session_events_endpoint(
    session_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    events = await build_admin_events(db, session_id)
    if events is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return events


@admin_router.get("/sessions/{session_id}/trace", response_model=AdminTraceResponse)
async def get_admin_session_trace_endpoint(
    session_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    trace = await build_admin_trace(db, session_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return trace


@admin_router.get("/sessions/{session_id}/policy-trace", response_model=AdminTraceResponse)
async def get_admin_session_policy_trace_alias_endpoint(
    session_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    return await get_admin_session_trace_endpoint(session_id=session_id, db=db)


@admin_router.get("/sessions/{session_id}/dreams", response_model=AdminDreamListResponse)
async def list_admin_session_dreams_endpoint(
    session_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    dreams = await list_admin_session_dreams(db, session_id)
    if dreams is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return AdminDreamListResponse(session_id=session_id, dreams=dreams)


@admin_router.get("/sessions/{session_id}/policy", response_model=AdminPolicyTraceListResponse)
async def list_admin_session_policy_endpoint(
    session_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    traces = await list_admin_policy_traces(db, session_id)
    if traces is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return traces


@admin_router.get("/dreams/{dream_id}", response_model=AdminDreamView)
async def get_admin_dream_endpoint(
    dream_id: int,
    db: AsyncSession = Depends(get_session),
):
    dream = await get_admin_dream(db, dream_id)
    if dream is None:
        raise HTTPException(status_code=404, detail="Dream not found")
    return dream


@admin_router.get("/prompts", response_model=AdminPromptListResponse)
async def list_admin_prompts_endpoint(db: AsyncSession = Depends(get_session)):
    return AdminPromptListResponse(prompts=await list_prompt_versions(db))


@admin_router.post("/prompts/{prompt_id}", response_model=AdminPromptVersionView)
async def create_admin_prompt_version_endpoint(
    prompt_id: UUID,
    payload: AdminPromptUpdateRequest,
    db: AsyncSession = Depends(get_session),
):
    prompt = await create_next_prompt_version(db, previous_id=prompt_id, content=payload.content)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt version not found")
    return prompt
