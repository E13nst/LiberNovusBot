# thirdparty
import pytest
from pydantic import ValidationError

# project
from services.analysis.schema.structured_dream_memory_v1 import StructuredDreamMemoryV1
from services.analysis_pipeline.memory_stages import build_structured_memory_from_provider_payload

pytestmark = pytest.mark.unit


def test_build_structured_memory_from_minimal_payload():
    payload = {
        "dream_details": ["Океан и разрушенный город"],
        "dream_ego_activity": ["плыву к берегу"],
        "figures": [{"name": "проводник", "role_hint": "помогает", "emotional_charge": "спокойствие"}],
        "emotional_field": ["тревога", "надежда"],
        "personal_context_questions": ["Что особенно выделялось во сне?"],
        "amplification_candidates": [{"symbol": "океан", "personal": "глубина"}],
        "compensation_hypotheses": [],
        "open_questions": ["Что было до разрушенного города?"],
        "recurring_motifs": ["океан"],
        "uncertainty_notes": [],
    }
    memory = build_structured_memory_from_provider_payload(payload)
    assert isinstance(memory, StructuredDreamMemoryV1)
    assert memory.dream_details == ["Океан и разрушенный город"]
    assert memory.emotional_field == ["тревога", "надежда"]
    assert len(memory.amplification_candidates) == 1
    assert memory.amplification_candidates[0].symbol == "океан"
    assert "океан" in memory.recurring_motifs


def test_build_structured_memory_rejects_extra_fields():
    payload = {"dream_details": ["кратко"], "unknown_field": "x"}
    with pytest.raises(ValidationError):
        build_structured_memory_from_provider_payload(payload)
