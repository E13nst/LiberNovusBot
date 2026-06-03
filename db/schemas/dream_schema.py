# stdlib
from uuid import UUID

# thirdparty
from pydantic import BaseModel, Field


class DreamCreate(BaseModel):
    text: str = Field(min_length=1)
    telegram_id: int
    telegram_first_name: str | None = None
    telegram_language_code: str | None = None


class DreamCreateResponse(BaseModel):
    status: str = "ok"
    messages: list[str] = Field(default_factory=list)
    session_id: UUID | None = None
    dream_id: int | None = None
