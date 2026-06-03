# stdlib
import inspect
from uuid import UUID

# thirdparty
import pytest
from sqlalchemy import func, select

# project
from db.models.dream_memory_model import DreamMemory
from db.models.session_analysis_model import SessionAnalysis
from services.analysis.schema.structured_dream_memory_v1 import StructuredDreamMemoryV1
from services.dream_intake import register_incoming_dream
from services.memory.memory_extractor import MEMORY_TEMPERATURE, MemoryExtractor
from services.memory.memory_prompt_builder import MemoryPromptInput, build_memory_prompt
from services.runtime.analysis_job_service import acquire_available_jobs
from services.runtime.analysis_runtime_executor import execute_analysis_job

pytestmark = pytest.mark.integration


class _SpyMemoryProvider:
    provider_name = "spy"
    model_name = "spy-v1"

    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.called_temperature = None

    async def generate(self, prompt: str, *, prompt_version: str, temperature: float | None = None):
        self.called_temperature = temperature
        from services.llm_providers.base import ProviderRawResponse, ProviderResponseMeta
        import json

        return ProviderRawResponse(
            raw_text=json.dumps(self.payload, ensure_ascii=False),
            meta=ProviderResponseMeta(
                provider=self.provider_name,
                model=self.model_name,
                prompt_version=prompt_version,
                latency_ms=1,
            ),
        )


def _memory_payload() -> dict:
    return {
        "dream_details": ["Иду по мосту над водой"],
        "dream_ego_activity": ["иду", "смотрю вниз"],
        "figures": [{"name": "сновидец", "role_hint": "наблюдатель", "emotional_charge": "тревога"}],
        "emotional_field": ["тревога"],
        "personal_context_questions": ["Что в этом моменте было самым ярким?"],
        "amplification_candidates": [{"symbol": "мост", "personal": "переход"}],
        "compensation_hypotheses": [],
        "open_questions": ["Куда вёл мост?"],
        "recurring_motifs": ["мост", "вода"],
        "uncertainty_notes": [],
    }


async def test_memory_prompt_has_explicit_no_interpretation_constraints():
    prompt = build_memory_prompt(
        MemoryPromptInput(
            session_id=UUID("00000000-0000-0000-0000-000000000001"),
            user_id=1,
            dream_id=1,
            dream_text="Я иду по мосту над тёмной водой.",
        )
    )
    lowered = prompt.lower()
    assert "нельзя интерпретировать" in lowered
    assert "нельзя использовать архетипы" in lowered
    assert "нельзя формулировать гипотезы" in lowered
    assert "без текста вне json" in lowered


async def test_memory_extractor_validates_structured_memory_and_uses_low_temperature(db_session, user_id):
    intake = await register_incoming_dream(db_session, telegram_id=user_id, text="Я иду по мосту над тёмной водой.")
    provider = _SpyMemoryProvider(_memory_payload())

    memory = await MemoryExtractor().extract(
        db_session,
        session_id=intake.dream.session_id,
        dream_id=intake.dream.id,
        provider=provider,  # type: ignore[arg-type]
    )

    assert isinstance(memory, StructuredDreamMemoryV1)
    assert provider.called_temperature == MEMORY_TEMPERATURE
    dump = memory.model_dump()
    assert "archetype" not in dump
    assert "shadow" not in dump
    assert "symbolic_interpretation" not in dump
    assert "jungian_interpretation" not in dump


async def test_memory_pipeline_does_not_depend_on_dream_analysis_v1():
    import services.memory.memory_extractor as extractor_module
    import services.memory.memory_orchestrator as orchestrator_module

    extractor_source = inspect.getsource(extractor_module)
    orchestrator_source = inspect.getsource(orchestrator_module)

    assert "DreamAnalysisV1" not in extractor_source
    assert "prepare_session_analysis" not in extractor_source
    assert "prepare_session_analysis" not in orchestrator_source


async def test_dream_memory_job_does_not_create_session_analysis(db_session, user_id):
    intake = await register_incoming_dream(db_session, telegram_id=user_id, text="Я перехожу мост через реку.")
    jobs = await acquire_available_jobs(db_session, limit=1, locked_by="memory-test-worker")
    assert len(jobs) == 1

    await execute_analysis_job(db_session, jobs[0])

    memory_count = await db_session.scalar(
        select(func.count()).select_from(DreamMemory).where(DreamMemory.dream_id == intake.dream.id)
    )
    analysis_count = await db_session.scalar(
        select(func.count()).select_from(SessionAnalysis).where(SessionAnalysis.session_id == intake.dream.session_id)
    )

    assert memory_count == 1
    assert analysis_count == 0
