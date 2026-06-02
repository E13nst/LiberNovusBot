# thirdparty
import pytest
from pydantic import ValidationError

# project
from services.analysis.schema.dream_analysis_v1 import DreamAnalysisV1


def _valid_payload(**overrides) -> dict:
    payload = {
        "summary": "Сон может отражать внутреннее напряжение между контролем и подавленными эмоциями.",
        "symbols": [
            {
                "symbol": "water",
                "meaning": "может указывать на эмоциональную глубину",
                "emotional_charge": "тревожная",
            }
        ],
        "emotional_state": {
            "primary": "тревога",
            "secondary": "напряжение",
            "intensity": 0.7,
        },
        "jungian_interpretation": {
            "archetypes": ["shadow"],
            "shadow_elements": ["подавленный страх"],
            "anima_animus_signals": [],
            "individuation_hint": "можно исследовать, что остаётся в тени",
        },
        "narrative_interpretation": "Сон может отражать напряжение между контролем и подавленными эмоциями.",
        "key_insight": "Важно заметить, что контроль может скрывать уязвимость.",
        "uncertainty_notes": ["Какие чувства сильнее всего остались после пробуждения?"],
    }
    payload.update(overrides)
    return payload


def test_valid_dream_analysis_v1_passes():
    validated = DreamAnalysisV1.model_validate(_valid_payload())
    assert validated.symbols[0].symbol == "water"
    assert validated.jungian_interpretation.archetypes == ["shadow"]
    assert validated.key_insight


def test_missing_required_field_fails():
    payload = _valid_payload()
    del payload["key_insight"]
    with pytest.raises(ValidationError):
        DreamAnalysisV1.model_validate(payload)


def test_wrong_field_type_fails():
    payload = _valid_payload()
    payload["emotional_state"]["intensity"] = "high"
    with pytest.raises(ValidationError):
        DreamAnalysisV1.model_validate(payload)


def test_intensity_out_of_bounds_fails():
    payload = _valid_payload()
    payload["emotional_state"]["intensity"] = 1.5
    with pytest.raises(ValidationError):
        DreamAnalysisV1.model_validate(payload)


def test_empty_symbols_with_interpretation_fails():
    with pytest.raises(ValidationError):
        DreamAnalysisV1.model_validate(_valid_payload(symbols=[]))


def test_extra_fields_forbidden():
    with pytest.raises(ValidationError):
        DreamAnalysisV1.model_validate(_valid_payload(extra_field="not allowed"))
