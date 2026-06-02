# thirdparty
import pytest

# project
from services.analysis.schema.dream_analysis_v1 import DreamAnalysisV1
from services.analysis_contract import AnalysisValidationError, validate_analysis_output


def _valid_payload(**overrides) -> dict:
    payload = {
        "summary": "Краткое резюме.",
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
            "individuation_hint": "можно исследовать тень",
        },
        "narrative_interpretation": "Сон может отражать внутреннее напряжение.",
        "key_insight": "Контроль может скрывать уязвимость.",
        "uncertainty_notes": ["Что осталось самым ярким?"],
    }
    payload.update(overrides)
    return payload


def test_validate_analysis_output_accepts_valid_payload():
    validated = validate_analysis_output(_valid_payload())
    assert isinstance(validated, DreamAnalysisV1)
    assert validated.key_insight


def test_validate_analysis_output_rejects_missing_field():
    payload = _valid_payload()
    del payload["summary"]
    with pytest.raises(AnalysisValidationError):
        validate_analysis_output(payload)


def test_validate_analysis_output_rejects_legacy_shape():
    with pytest.raises(AnalysisValidationError):
        validate_analysis_output(
            {
                "interpretation": "legacy",
                "themes": ["water"],
                "questions_for_user": ["q"],
            }
        )
