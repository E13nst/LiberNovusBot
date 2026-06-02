# stdlib
from datetime import datetime
import json
import logging
from uuid import uuid4

# thirdparty
import pytest
from fastapi import HTTPException

# project
from db.models.dream_model import Dream
from db.models.session_model import DreamSession
from db.models.session_summary_model import SessionSummary
from services.analysis_contract import AnalysisValidationError, validate_analysis_output
from services.analysis_input_service import AnalysisInputContext, load_analysis_input
from services.analysis_orchestrator import run_session_analysis
from services.jungian_prompt_builder import build_jungian_prompt
from services.llm_providers.base import (
    LLMProvider,
    ProviderRawResponse,
    ProviderResponseMeta,
    ProviderTerminalError,
    ProviderTransportError,
)
from services.llm_providers.mock_provider import MockLLMProvider
from services.runtime.runtime_types import NonRetryableAnalysisError
from tests.fixtures.dream_analysis_v1 import sample_dream_analysis_v1_json
from services.session_analysis_service import get_session_analysis


pytestmark = pytest.mark.integration


class _InvalidProvider(LLMProvider):
    provider_name = "invalid"
    model_name = "invalid-v1"

    async def generate(self, prompt: str, *, prompt_version: str) -> ProviderRawResponse:
        return ProviderRawResponse(
            raw_text=json.dumps({"invalid": True}),
            meta=ProviderResponseMeta(
                provider=self.provider_name,
                model=self.model_name,
                prompt_version=prompt_version,
                latency_ms=1,
            ),
        )


class _TerminalProvider(LLMProvider):
    provider_name = "terminal"
    model_name = "terminal-v1"

    async def generate(self, prompt: str, *, prompt_version: str) -> ProviderRawResponse:
        raise ProviderTerminalError("hard provider failure")


class _FlakyProvider(LLMProvider):
    provider_name = "flaky"
    model_name = "flaky-v1"

    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, prompt: str, *, prompt_version: str) -> ProviderRawResponse:
        self.calls += 1
        if self.calls == 1:
            raise ProviderTransportError("transient")
        payload = sample_dream_analysis_v1_json(
            narrative_interpretation="ok",
            key_insight="insight",
            uncertainty_notes=["q"],
        )
        return ProviderRawResponse(
            raw_text=json.dumps(payload),
            meta=ProviderResponseMeta(
                provider=self.provider_name,
                model=self.model_name,
                prompt_version=prompt_version,
                latency_ms=1,
            ),
        )


def _make_context(*, dream_text: str = "dark corridor blocked passage") -> AnalysisInputContext:
    session = DreamSession(user_id=123456789, status="active")
    summary = SessionSummary(
        session_id=session.id,
        user_id=session.user_id,
        dream_count=1,
        key_symbols=["corridor", "passage"],
        recurring_words=[],
        raw_text_sample=dream_text,
    )
    dreams = [
        Dream(
            user_id=session.user_id,
            text=dream_text,
            session_id=session.id,
            created_at=datetime.utcnow(),
        )
    ]
    return AnalysisInputContext(session=session, session_summary=summary, dreams=dreams)


async def test_mock_provider_returns_valid_json():
    provider = MockLLMProvider()
    payload = await provider.generate("test prompt", prompt_version="v1")
    validated = validate_analysis_output(json.loads(payload.raw_text))

    assert validated.symbols
    assert validated.jungian_interpretation.archetypes
    assert validated.key_insight


async def test_mock_provider_is_deterministic_for_same_prompt():
    provider = MockLLMProvider()
    first = await provider.generate("same prompt", prompt_version="v1")
    second = await provider.generate("same prompt", prompt_version="v1")

    assert first == second


async def test_mock_provider_differs_for_different_prompts():
    provider = MockLLMProvider()
    first = await provider.generate("prompt a", prompt_version="v1")
    second = await provider.generate("prompt b", prompt_version="v1")

    assert first != second


async def test_validate_analysis_output_rejects_invalid_json():
    with pytest.raises(AnalysisValidationError):
        validate_analysis_output({"summary": "only partial payload"})


async def test_prompt_builder_integration_from_context():
    context = _make_context()
    prompt = build_jungian_prompt(
        context.session_summary,
        context.dreams,
        last_activity_at=context.session.last_activity_at,
        session_created_at=context.session.created_at,
    )

    assert "[CONTROLLED JUNGIAN PROMPT v2]" in prompt
    assert "Сон не имеет фиксированного значения." in prompt
    assert "blocked passage" in prompt or "dark corridor" in prompt


async def test_orchestrator_saves_result(db_session, user_id):
    session = DreamSession(user_id=user_id, status="active")
    db_session.add(session)
    await db_session.flush()

    summary = SessionSummary(
        session_id=session.id,
        user_id=user_id,
        dream_count=1,
        key_symbols=["water"],
        recurring_words=[],
        raw_text_sample="river and bridge",
    )
    db_session.add(summary)

    dream = Dream(
        user_id=user_id,
        text="I crossed a bridge over dark water",
        session_id=session.id,
    )
    db_session.add(dream)
    await db_session.flush()

    context = await load_analysis_input(db_session, session.id)
    saved = await run_session_analysis(db_session, context)

    assert saved.session_id == session.id
    assert saved.provider == "mock"
    assert saved.model == "mock-v1"
    assert saved.prompt_version == "v2"
    assert saved.analysis_version == "dream_v1"
    assert saved.analysis_json["symbols"]
    assert saved.analysis_json["key_insight"]

    loaded = await get_session_analysis(db_session, session.id)
    assert loaded is not None
    assert loaded.id == saved.id


async def test_orchestrator_continue_appends_history(db_session, user_id):
    session = DreamSession(user_id=user_id, status="active")
    db_session.add(session)
    await db_session.flush()

    summary = SessionSummary(
        session_id=session.id,
        user_id=user_id,
        dream_count=1,
        key_symbols=["forest"],
        recurring_words=[],
        raw_text_sample="deep forest path",
    )
    db_session.add(summary)

    dream = Dream(user_id=user_id, text="walking through a deep forest", session_id=session.id)
    db_session.add(dream)
    await db_session.flush()

    context = await load_analysis_input(db_session, session.id)
    first = await run_session_analysis(db_session, context)
    second = await run_session_analysis(db_session, context)

    assert first.session_id == second.session_id
    assert first.thread_id == second.thread_id
    assert first.id != second.id
    assert first.continuation_index == 0
    assert second.continuation_index == 1
    assert second.is_latest is True
    assert first.is_latest is False

    loaded = await get_session_analysis(db_session, session.id)
    assert loaded is not None
    assert loaded.id == second.id


async def test_orchestrator_raises_on_invalid_provider_json(db_session, user_id, caplog):
    session = DreamSession(user_id=user_id, status="active")
    db_session.add(session)
    await db_session.flush()

    summary = SessionSummary(
        session_id=session.id,
        user_id=user_id,
        dream_count=0,
        key_symbols=[],
        recurring_words=[],
        raw_text_sample=None,
    )
    context = AnalysisInputContext(session=session, session_summary=summary, dreams=[])

    with caplog.at_level(logging.INFO, logger="services.analysis_orchestrator"):
        with pytest.raises(NonRetryableAnalysisError):
            await run_session_analysis(db_session, context, provider=_InvalidProvider())

    assert any(
        record.message == "LLM provider inference completed"
        and getattr(record, "session_id", None) == str(session.id)
        for record in caplog.records
    )
    assert any(
        record.message == "LLM analysis contract validation failed"
        and getattr(record, "contract_success", None) is False
        and getattr(record, "session_id", None) == str(session.id)
        for record in caplog.records
    )


async def test_orchestrator_maps_terminal_provider_failure_to_non_retryable(db_session, user_id):
    session = DreamSession(user_id=user_id, status="active")
    db_session.add(session)
    await db_session.flush()

    summary = SessionSummary(
        session_id=session.id,
        user_id=user_id,
        dream_count=0,
        key_symbols=[],
        recurring_words=[],
        raw_text_sample=None,
    )
    context = AnalysisInputContext(session=session, session_summary=summary, dreams=[])

    with pytest.raises(NonRetryableAnalysisError):
        await run_session_analysis(db_session, context, provider=_TerminalProvider())


async def test_orchestrator_retries_transient_provider_failures(db_session, user_id, monkeypatch):
    monkeypatch.setattr("settings.LLM_MAX_ATTEMPTS", 2)

    session = DreamSession(user_id=user_id, status="active")
    db_session.add(session)
    await db_session.flush()

    summary = SessionSummary(
        session_id=session.id,
        user_id=user_id,
        dream_count=0,
        key_symbols=[],
        recurring_words=[],
        raw_text_sample=None,
    )
    context = AnalysisInputContext(session=session, session_summary=summary, dreams=[])
    provider = _FlakyProvider()

    saved = await run_session_analysis(db_session, context, provider=provider)

    assert provider.calls == 2
    assert saved.provider == "flaky"


async def test_load_analysis_input_builds_summary_when_missing(db_session, user_id):
    session = DreamSession(user_id=user_id, status="active")
    db_session.add(session)
    await db_session.flush()

    dream = Dream(user_id=user_id, text="flying over mountains at dawn", session_id=session.id)
    db_session.add(dream)
    await db_session.flush()

    context = await load_analysis_input(db_session, session.id)

    assert context.session.id == session.id
    assert context.session_summary.dream_count == 1
    assert len(context.dreams) == 1


async def test_load_analysis_input_raises_for_unknown_session(db_session):
    with pytest.raises(HTTPException) as exc_info:
        await load_analysis_input(db_session, uuid4())

    assert exc_info.value.status_code == 404
