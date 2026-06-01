# thirdparty
import pytest

# project
from services.analysis_contract import validate_analysis_output
from services.analysis_orchestrator import run_session_analysis
from services.response_parser import extract_json, parse_json
from services.runtime.runtime_types import NonRetryableAnalysisError, RetryableAnalysisError
from services.session_analysis_service import get_session_analysis
from tests.smoke.conftest import seed_smoke_session

pytestmark = pytest.mark.integration


@pytest.mark.openai_smoke
async def test_real_openai_analysis_persists_contract_valid_session_analysis(
    db_session,
    user_id,
    openai_smoke_provider,
    openai_smoke_runtime_config,
):
    """Dream -> prompt -> OpenAI -> parser -> contract -> session_analyses (no runtime queue)."""
    session = await seed_smoke_session(db_session, user_id)

    try:
        saved = await run_session_analysis(
            db_session,
            session.id,
            provider=openai_smoke_provider,
        )
    except (RetryableAnalysisError, NonRetryableAnalysisError) as exc:
        raw = openai_smoke_provider.last_response
        if raw is not None:
            pytest.fail(
                f"run_session_analysis failed after provider returned output: {exc}\n"
                f"provider={raw.meta.provider} model={raw.meta.model} "
                f"latency_ms={raw.meta.latency_ms} usage={raw.meta.usage}"
            )
        raise

    assert openai_smoke_provider.call_count == 1
    raw = openai_smoke_provider.last_response
    assert raw is not None
    assert raw.raw_text.strip()
    assert raw.meta.provider == "openai"
    assert raw.meta.model == openai_smoke_runtime_config.default_model
    assert raw.meta.latency_ms > 0
    if raw.meta.usage is not None:
        assert raw.meta.usage.total_tokens > 0

    raw_json = extract_json(raw.raw_text)
    parsed_payload = parse_json(raw_json)
    validated = validate_analysis_output(parsed_payload)

    assert saved.session_id == session.id
    assert saved.provider == "openai"
    assert saved.model == openai_smoke_runtime_config.default_model
    assert saved.prompt_version
    assert saved.analysis_version
    assert saved.raw_response == raw.raw_text
    assert saved.analysis_json == validated.model_dump()

    loaded = await get_session_analysis(db_session, session.id)
    assert loaded is not None
    assert loaded.id == saved.id
    assert loaded.provider == "openai"
    validate_analysis_output(loaded.analysis_json)


def test_openai_smoke_skipped_without_opt_in(monkeypatch):
    """Default pytest runs must not call OpenAI."""
    monkeypatch.delenv("RUN_OPENAI_SMOKE", raising=False)
    monkeypatch.setenv("ENV_MODE", "test")
    monkeypatch.setenv("LLM_PROVIDER", "mock")

    from tests.smoke.conftest import openai_smoke_skip_reason

    assert openai_smoke_skip_reason() is not None
