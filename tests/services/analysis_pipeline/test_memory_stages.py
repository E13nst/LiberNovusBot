# thirdparty
import pytest

# project
from services.analysis.schema.structured_dream_memory_v1 import StructuredDreamMemoryV1
from services.analysis_pipeline.memory_stages import build_structured_memory_from_provider_payload

pytestmark = pytest.mark.unit


def test_build_structured_memory_from_minimal_payload():
    payload = {
        "summary": "Океан и разрушенный город",
        "symbols": [{"symbol": "океан", "meaning": "глубина"}],
        "emotional_state": {"primary": "тревога", "secondary": "надежда"},
        "jungian_interpretation": {"archetypes": ["Путешествие"]},
    }
    memory = build_structured_memory_from_provider_payload(payload)
    assert isinstance(memory, StructuredDreamMemoryV1)
    assert memory.dream_details == ["Океан и разрушенный город"]
    assert memory.emotional_field == ["тревога", "надежда"]
    assert len(memory.amplification_candidates) == 1
    assert memory.amplification_candidates[0].symbol == "океан"
    assert "океан" in memory.recurring_motifs


def test_build_structured_memory_rejects_extra_fields():
    payload = {"summary": "кратко", "unknown_field": "x"}
    memory = build_structured_memory_from_provider_payload(payload)
    assert memory.model_dump().get("unknown_field") is None
