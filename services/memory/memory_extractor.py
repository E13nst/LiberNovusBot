# stdlib
from dataclasses import dataclass
import logging
from uuid import UUID

# thirdparty
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# project
from db.models.dream_model import Dream
from db.models.session_model import DreamSession
from services.analysis.schema.structured_dream_memory_v1 import StructuredDreamMemoryV1
from services.analysis_policy_service import generate_with_retry
from services.llm_providers.base import LLMProvider, ProviderTerminalError, ProviderTransportError, SDKUnexpectedError
from services.llm_providers.registry import get_provider
from services.memory.memory_prompt_builder import MemoryPromptInput, build_memory_prompt
from services.response_parser import ResponseParseError, extract_json, parse_json
from services.runtime.runtime_types import NonRetryableAnalysisError, RetryableAnalysisError

logger = logging.getLogger(__name__)

MEMORY_PROMPT_VERSION = "memory_v1"
MEMORY_TEMPERATURE = 0.0

_FORBIDDEN_INTERPRETIVE_MARKERS: tuple[str, ...] = (
    "архетип",
    "тень",
    "символиз",
    "означа",
    "скрытый смысл",
    "юнгиан",
)


@dataclass(frozen=True)
class MemoryInputContext:
    session: DreamSession
    dream: Dream


async def prepare_memory_input(
    db: AsyncSession,
    *,
    session_id: UUID,
    dream_id: int,
) -> MemoryInputContext:
    session = await db.get(DreamSession, session_id)
    if session is None:
        raise NonRetryableAnalysisError(f"Session {session_id} not found")
    dream = await db.scalar(select(Dream).where(Dream.id == dream_id, Dream.session_id == session_id))
    if dream is None:
        raise NonRetryableAnalysisError(f"Dream {dream_id} not found for session {session_id}")
    return MemoryInputContext(session=session, dream=dream)


class MemoryExtractor:
    async def extract(
        self,
        db: AsyncSession,
        *,
        session_id: UUID,
        dream_id: int,
        provider: LLMProvider | None = None,
    ) -> StructuredDreamMemoryV1:
        context = await prepare_memory_input(db, session_id=session_id, dream_id=dream_id)
        prompt = build_memory_prompt(
            MemoryPromptInput(
                session_id=context.session.id,
                user_id=context.session.user_id,
                dream_id=context.dream.id,
                dream_text=context.dream.text,
                session_created_at=context.session.created_at,
                session_last_activity_at=context.session.last_activity_at,
                dream_created_at=context.dream.created_at,
            )
        )
        llm = provider or get_provider()
        try:
            raw = await generate_with_retry(
                llm,
                prompt,
                MEMORY_PROMPT_VERSION,
                logger,
                temperature=MEMORY_TEMPERATURE,
            )
        except ProviderTransportError as exc:
            raise RetryableAnalysisError(str(exc)) from exc
        except (ProviderTerminalError, SDKUnexpectedError) as exc:
            raise NonRetryableAnalysisError(str(exc)) from exc

        try:
            payload = parse_json(extract_json(raw.raw_text))
        except ResponseParseError as exc:
            raise NonRetryableAnalysisError(str(exc)) from exc

        memory = StructuredDreamMemoryV1.model_validate(payload)
        return _sanitize_memory(memory)


def _sanitize_memory(memory: StructuredDreamMemoryV1) -> StructuredDreamMemoryV1:
    for value in _iter_strings(memory.model_dump()):
        lowered = value.lower()
        if any(marker in lowered for marker in _FORBIDDEN_INTERPRETIVE_MARKERS):
            raise NonRetryableAnalysisError("Memory payload contains interpretive markers")
    return memory


def _iter_strings(value):
    if isinstance(value, str):
        yield value
        return
    if isinstance(value, dict):
        for item in value.values():
            yield from _iter_strings(item)
        return
    if isinstance(value, list):
        for item in value:
            yield from _iter_strings(item)
