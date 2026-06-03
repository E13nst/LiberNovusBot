# thirdparty
from pydantic import BaseModel, Field


class TelegramUser(BaseModel):
    id: int
    first_name: str | None = None
    language_code: str | None = None


class TelegramChat(BaseModel):
    id: int


class TelegramMessage(BaseModel):
    from_user: TelegramUser = Field(alias="from")
    chat: TelegramChat
    text: str = Field(min_length=1)


class TelegramUpdate(BaseModel):
    update_id: int
    message: TelegramMessage | None = None

    model_config = {"populate_by_name": True}


class TelegramWebhookResponse(BaseModel):
    ok: bool = True
