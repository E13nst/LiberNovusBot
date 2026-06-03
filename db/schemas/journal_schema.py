# stdlib
from datetime import datetime
from typing import Any
from uuid import UUID

# thirdparty
from pydantic import BaseModel, Field


class JournalSessionListItem(BaseModel):
    id: UUID
    status: str
    created_at: datetime
    last_activity_at: datetime
    dream_count: int


class JournalDreamListItem(BaseModel):
    id: int
    session_id: UUID
    created_at: datetime
    excerpt: str
    has_memory: bool


class JournalDreamDetail(BaseModel):
    id: int
    session_id: UUID
    text: str
    created_at: datetime
    memory_json: dict[str, Any] | None = None
    dialogue_turns: list[dict[str, Any]] = Field(default_factory=list)


class JournalPatternSummary(BaseModel):
    recurring_symbols: list[dict[str, Any]] = Field(default_factory=list)
    recurring_words: list[dict[str, Any]] = Field(default_factory=list)
