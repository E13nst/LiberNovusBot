# thirdparty
from pydantic import BaseModel, ConfigDict, Field, field_validator

_BackgroundNoteValue = str | list[str]


def _coerce_background_note_value(raw: object) -> _BackgroundNoteValue | None:
    if isinstance(raw, str):
        return raw
    if isinstance(raw, bool):
        return "true" if raw else "false"
    if isinstance(raw, (int, float)):
        return str(raw)
    if isinstance(raw, list):
        coerced: list[str] = []
        for item in raw:
            if isinstance(item, str):
                coerced.append(item)
            elif isinstance(item, bool):
                coerced.append("true" if item else "false")
            elif isinstance(item, (int, float)):
                coerced.append(str(item))
        return coerced
    return None


def _normalize_background_notes(value: object) -> dict[str, _BackgroundNoteValue]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, _BackgroundNoteValue] = {}
    for key, raw in value.items():
        if not isinstance(key, str):
            continue
        coerced = _coerce_background_note_value(raw)
        if coerced is not None:
            normalized[key] = coerced
    return normalized


_FORBIDDEN_PHRASES = (
    "это означает",
    "ваш сон говорит",
    "вы точно",
    "главный смысл сна",
    "основное значение сна",
    "это значит",
)


class DialogueTurnV1(BaseModel):
    """User-facing companion turn contract."""

    model_config = ConfigDict(extra="forbid")

    assistant_message: str
    focus: list[str] = Field(default_factory=list, max_length=3)
    questions: list[str] = Field(default_factory=list, max_length=3)
    background_notes: dict[str, str | list[str]] = Field(default_factory=dict)
    emotional_intensity: float = Field(default=0.5, ge=0.0, le=1.0)
    safety_flags: list[str] = Field(default_factory=list)

    @field_validator("background_notes", mode="before")
    @classmethod
    def _normalize_background_notes(cls, value: object) -> dict[str, _BackgroundNoteValue]:
        return _normalize_background_notes(value)

    @field_validator("assistant_message")
    @classmethod
    def _reject_authoritarian_language(cls, value: str) -> str:
        lowered = value.lower()
        for phrase in _FORBIDDEN_PHRASES:
            if phrase in lowered:
                raise ValueError(f"assistant_message contains forbidden phrase: {phrase}")
        stripped = value.strip()
        if len(stripped) < 20:
            raise ValueError("assistant_message is too short for a companion turn")
        return stripped

    @field_validator("questions")
    @classmethod
    def _limit_questions(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()][:3]
