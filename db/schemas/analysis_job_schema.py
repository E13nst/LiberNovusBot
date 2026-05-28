# stdlib
from datetime import datetime
from uuid import UUID

# thirdparty
from pydantic import BaseModel, ConfigDict


class AnalysisJobCreateResponseSchema(BaseModel):
    job_id: UUID
    status: str


class AnalysisJobSchema(BaseModel):
    id: UUID
    session_id: UUID
    thread_id: UUID | None
    status: str
    provider: str
    model: str
    mode: str
    attempts: int
    max_attempts: int
    last_error_class: str | None
    last_error_message: str | None
    retryable: bool
    created_at: datetime
    updated_at: datetime
    available_after: datetime
    started_at: datetime | None
    completed_at: datetime | None
    locked_by: str | None
    locked_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class AnalysisJobHistorySchema(BaseModel):
    session_id: UUID
    jobs: list[AnalysisJobSchema]
