# stdlib
import logging
from uuid import UUID

# thirdparty
from sqlalchemy.ext.asyncio import AsyncSession

# project
from db.models.session_analysis_model import SessionAnalysis
from services.analysis_contract import (
    ANALYSIS_VERSION,
    AnalysisValidationError,
    DEFAULT_PROMPT_VERSION,
    validate_analysis_output,
)
from services.analysis_continuation_service import AnalysisModeRequest, resolve_thread_for_analysis
from services.analysis_input_service import AnalysisInputContext, load_analysis_input
from services.analysis_policy_service import generate_with_retry
from services.analysis_thread_service import save_analysis_in_thread
from services.jungian_prompt_builder import build_jungian_prompt
from services.llm_providers.base import LLMProvider, ProviderTransportError
from services.llm_providers.registry import get_provider
from services.response_parser import ResponseParseError, extract_json, parse_json
from services.runtime.runtime_types import NonRetryableAnalysisError, RetryableAnalysisError

logger = logging.getLogger(__name__)


async def run_session_analysis(
    db: AsyncSession,
    session_id: UUID | AnalysisInputContext,
    *,
    mode: AnalysisModeRequest = "auto",
    provider: LLMProvider | None = None,
    prompt_version: str = DEFAULT_PROMPT_VERSION,
) -> SessionAnalysis:
    """Execute analysis pipeline: prompt builder -> provider -> parse -> validate -> persist."""
    context = (
        session_id
        if isinstance(session_id, AnalysisInputContext)
        else await load_analysis_input(db, session_id)
    )
    llm = provider or get_provider()

    prompt = build_jungian_prompt(
        context.session_summary,
        context.dreams,
        last_activity_at=context.session.last_activity_at,
        session_created_at=context.session.created_at,
    )

    try:
        raw_result = await generate_with_retry(llm, prompt, prompt_version, logger)
    except ProviderTransportError as exc:
        raise RetryableAnalysisError(str(exc)) from exc

    try:
        raw_json = extract_json(raw_result.raw_text)
        parsed_payload = parse_json(raw_json)
        validated = validate_analysis_output(parsed_payload)
    except (ResponseParseError, AnalysisValidationError) as exc:
        raise NonRetryableAnalysisError(str(exc)) from exc

    raw_response = raw_result.raw_text
    provider_name = raw_result.meta.provider
    model_name = raw_result.meta.model
    logger.info(
        "LLM analysis generated",
        extra={
            "provider": provider_name,
            "model": model_name,
            "prompt_version": raw_result.meta.prompt_version,
            "latency_ms": raw_result.meta.latency_ms,
            "usage": raw_result.meta.usage.__dict__ if raw_result.meta.usage else None,
        },
    )

    thread, _resolved_mode = await resolve_thread_for_analysis(db, context.session.id, mode)

    return await save_analysis_in_thread(
        db,
        thread,
        session_id=context.session.id,
        user_id=context.session.user_id,
        provider=provider_name,
        model=model_name,
        prompt_version=prompt_version,
        analysis_version=ANALYSIS_VERSION,
        analysis_json=validated.model_dump(),
        raw_response=raw_response,
    )
