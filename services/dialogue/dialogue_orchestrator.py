# stdlib
import logging
from datetime import datetime, timezone

# thirdparty
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

# project
from services.analysis_policy_service import generate_with_retry
from services.conversation.conversation_turn_service import get_previous_user_message_at, list_recent_turns
from services.dialogue.dialogue_prompt import build_dialogue_prompt, sanitize_language_code
from services.dialogue.schema.dialogue_turn_v1 import DialogueTurnV1
from services.dialogue.user_display_name import sanitize_user_display_name
from services.llm_providers.base import LLMProvider, ProviderTerminalError, ProviderTransportError, SDKUnexpectedError
from services.llm_providers.registry import get_provider
from services.response_parser import ResponseParseError, extract_json, parse_json
from services.session_summary_service import get_session_summary

logger = logging.getLogger(__name__)

DIALOGUE_PROMPT_VERSION = "dialogue_v1"


def _format_recent_dialogue(turns) -> str:
    lines: list[str] = []
    for turn in turns:
        prefix = "Пользователь" if turn.role == "user" else "Спутник"
        lines.append(f"{prefix}: {turn.text}")
    return "\n".join(lines)


def _format_session_context(summary) -> str:
    if summary is None:
        return ""
    symbols = ", ".join(summary.key_symbols) if summary.key_symbols else "—"
    words = ", ".join(summary.recurring_words) if summary.recurring_words else "—"
    return (
        f"dream_count: {summary.dream_count}\n"
        f"key_symbols: {symbols}\n"
        f"recurring_words: {words}"
    )


async def generate_dialogue_turn(
    db: AsyncSession,
    *,
    session_id: UUID,
    user_message: str,
    user_display_name: str | None = None,
    user_language_code: str | None = None,
    provider: LLMProvider | None = None,
    now: datetime | None = None,
) -> DialogueTurnV1:
    display_name = sanitize_user_display_name(user_display_name)
    language = sanitize_language_code(user_language_code)
    current_time = now or datetime.now(timezone.utc)
    previous_user_at = await get_previous_user_message_at(db, session_id)
    summary = await get_session_summary(db, session_id)
    recent = await list_recent_turns(db, session_id, limit=10)
    prompt = build_dialogue_prompt(
        user_message=user_message,
        session_context=_format_session_context(summary),
        recent_dialogue=_format_recent_dialogue(recent),
        user_display_name=display_name,
        user_language_code=language,
        current_time_utc=current_time,
        last_user_message_at=previous_user_at,
    )
    llm = provider or get_provider()
    try:
        raw_result = await generate_with_retry(llm, prompt, DIALOGUE_PROMPT_VERSION, logger)
    except (ProviderTerminalError, SDKUnexpectedError) as exc:
        raise RuntimeError(str(exc)) from exc
    except ProviderTransportError as exc:
        raise RuntimeError(str(exc)) from exc

    try:
        raw_json = extract_json(raw_result.raw_text)
        parsed = parse_json(raw_json)
    except ResponseParseError as exc:
        raise RuntimeError(str(exc)) from exc

    return DialogueTurnV1.model_validate(parsed)
