# thirdparty
from pydantic import BaseModel, Field


class DreamCreate(BaseModel):
    text: str = Field(min_length=1)
    telegram_id: int


class DreamCreateResponse(BaseModel):
    status: str = "ok"
