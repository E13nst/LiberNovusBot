# stdlib
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

# project
from services.prompts.memory.builder import (
    build_memory_extraction_instructions,
    build_memory_prompt_rules,
    build_memory_prompt_sections,
)


@dataclass(frozen=True)
class MemoryPromptInput:
    session_id: UUID
    user_id: int
    dream_id: int
    dream_text: str
    session_created_at: datetime | None = None
    session_last_activity_at: datetime | None = None
    dream_created_at: datetime | None = None


def _format_utc(value: datetime | None) -> str:
    if value is None:
        return "null"
    normalized = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return normalized.astimezone(timezone.utc).isoformat(timespec="seconds")


def build_memory_prompt(payload: MemoryPromptInput) -> str:
    metadata = "\n".join(
        (
            "## Metadata",
            f"session_id: {payload.session_id}",
            f"user_id: {payload.user_id}",
            f"dream_id: {payload.dream_id}",
            f"session_created_at_utc: {_format_utc(payload.session_created_at)}",
            f"session_last_activity_at_utc: {_format_utc(payload.session_last_activity_at)}",
            f"dream_created_at_utc: {_format_utc(payload.dream_created_at)}",
        )
    )
    dream_input = "\n".join(("## Dream Input (raw text)", payload.dream_text.strip() or "(empty)"))
    return build_memory_prompt_sections(
        (
            "## Memory Extraction Mode",
            build_memory_prompt_rules(),
            build_memory_extraction_instructions(),
            metadata,
            dream_input,
        )
    )
