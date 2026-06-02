# stdlib
import json

# thirdparty
import pytest

# project
from services.analysis_contract import validate_analysis_output
from services.analysis_orchestrator import run_session_analysis
from services.llm_providers.base import LLMProvider, ProviderRawResponse, ProviderResponseMeta, ProviderUsage
from services.llm_providers.mock_provider import MockLLMProvider
from tests.fixtures.dream_analysis_v1 import sample_dream_analysis_v1_json


pytestmark = pytest.mark.integration


class _OpenAIStubProvider(LLMProvider):
    """Minimal OpenAI-path stub; orchestrator contract unchanged."""

    provider_name = "openai"
    model_name = "gpt-4o-mini"

    async def generate(self, prompt: str, *, prompt_version: str) -> ProviderRawResponse:
        payload = sample_dream_analysis_v1_json()
        return ProviderRawResponse(
            raw_text=json.dumps(payload),
            meta=ProviderResponseMeta(
                provider=self.provider_name,
                model=self.model_name,
                prompt_version=prompt_version,
                latency_ms=5,
                usage=ProviderUsage(prompt_tokens=1, completion_tokens=2, total_tokens=3),
            ),
        )


async def test_mock_to_openai_provider_switch_without_orchestrator_changes(db_session, user_id):
    from db.models.dream_model import Dream
    from db.models.session_model import DreamSession
    from db.models.session_summary_model import SessionSummary
    from services.analysis_input_service import load_analysis_input

    session = DreamSession(user_id=user_id, status="active")
    db_session.add(session)
    await db_session.flush()

    summary = SessionSummary(
        session_id=session.id,
        user_id=user_id,
        dream_count=1,
        key_symbols=["water"],
        recurring_words=[],
        raw_text_sample="river",
    )
    db_session.add(summary)
    dream = Dream(user_id=user_id, text="river crossing", session_id=session.id)
    db_session.add(dream)
    await db_session.flush()

    context = await load_analysis_input(db_session, session.id)

    mock_saved = await run_session_analysis(db_session, context, provider=MockLLMProvider())
    assert mock_saved.provider == "mock"

    openai_saved = await run_session_analysis(db_session, context, provider=_OpenAIStubProvider())
    assert openai_saved.provider == "openai"
    assert openai_saved.model == "gpt-4o-mini"
    validate_analysis_output(openai_saved.analysis_json)
