# stdlib
from datetime import datetime
from uuid import UUID

# thirdparty
from pydantic import BaseModel, ConfigDict


class SessionSummarySchema(BaseModel):
    id: UUID
    session_id: UUID
    user_id: int
    dream_count: int
    key_symbols: list[str]
    recurring_words: list[str]
    raw_text_sample: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
