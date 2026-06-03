from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

AdminEventType = Literal[
    "INPUT",
    "POLICY",
    "DREAM_CREATED",
    "JOB_ENQUEUED",
    "REFLECTION_READY",
    "CLARIFICATION",
]


class AdminSessionListItem(BaseModel):
    id: UUID
    user_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    last_activity_at: datetime
    dream_count: int
    job_count: int
    analysis_count: int


class AdminSessionListResponse(BaseModel):
    sessions: list[AdminSessionListItem]


class AdminSessionDetail(AdminSessionListItem):
    policy_trace_count: int


class AdminDreamView(BaseModel):
    id: int
    user_id: int
    session_id: UUID
    text: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminDreamListResponse(BaseModel):
    session_id: UUID
    dreams: list[AdminDreamView]


class AdminUserListItem(BaseModel):
    user_id: int
    session_count: int
    dream_count: int
    last_activity_at: datetime | None = None


class AdminUserListResponse(BaseModel):
    users: list[AdminUserListItem]


class AdminGlobalDreamListResponse(BaseModel):
    dreams: list[AdminDreamView]


class EventView(BaseModel):
    id: str
    type: AdminEventType
    timestamp: datetime
    payload: dict[str, Any] = Field(default_factory=dict)
    session_id: UUID
    user_id: int


class AdminEventListResponse(BaseModel):
    session_id: UUID
    events: list[EventView]


class AdminTraceResponse(BaseModel):
    session_id: UUID
    timeline: list[EventView]


class AdminPolicyTraceView(BaseModel):
    id: UUID
    session_id: UUID | None
    user_id: int
    route: str
    reason_code: str
    input: dict[str, Any]
    decision: dict[str, Any]
    outcome: dict[str, Any]
    dream_id: int | None
    job_id: UUID | None
    created_at: datetime


class AdminPolicyTraceListResponse(BaseModel):
    session_id: UUID
    policy_traces: list[AdminPolicyTraceView]


class AdminPromptVersionView(BaseModel):
    id: UUID
    prompt_type: str
    version: int
    content: str
    active_flag: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminPromptListResponse(BaseModel):
    prompts: list[AdminPromptVersionView]


class AdminPromptUpdateRequest(BaseModel):
    content: str = Field(min_length=1)
