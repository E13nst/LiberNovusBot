# stdlib
from datetime import datetime
from uuid import UUID

# thirdparty
from pydantic import BaseModel, ConfigDict

# project
from services.analysis.dto.dream_analysis_legacy_mapper import LegacyAnalysisPayload


class LegacyAnalysisPayloadSchema(LegacyAnalysisPayload):
    """API presentation schema for legacy-compatible analysis fields."""


class SessionAnalysisSchema(BaseModel):
    id: UUID
    session_id: UUID
    thread_id: UUID
    user_id: int
    provider: str
    model: str
    prompt_version: str
    analysis_version: str
    analysis_json: LegacyAnalysisPayloadSchema
    raw_response: str | None
    is_latest: bool
    continuation_index: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionAnalysisItemSchema(BaseModel):
    id: UUID
    created_at: datetime
    is_latest: bool
    continuation_index: int
    provider: str
    model: str
    prompt_version: str
    analysis_version: str
    analysis_json: LegacyAnalysisPayloadSchema
    raw_response: str | None

    model_config = ConfigDict(from_attributes=True)


class SessionAnalysisThreadGroupSchema(BaseModel):
    thread_id: UUID
    status: str
    analyses: list[SessionAnalysisItemSchema]


class SessionAnalysisHistorySchema(BaseModel):
    session_id: UUID
    threads: list[SessionAnalysisThreadGroupSchema]
