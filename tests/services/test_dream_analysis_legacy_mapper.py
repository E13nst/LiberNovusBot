# thirdparty
import pytest

# project
from services.analysis.dto.dream_analysis_legacy_mapper import LegacyMapperV1
from services.analysis.schema.dream_analysis_v1 import DreamAnalysisV1


def _canonical(**overrides) -> DreamAnalysisV1:
    payload = {
        "summary": "Краткое резюме сна.",
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
        "uncertainty_notes": ["Что осталось самым ярким после пробуждения?"],
    }
    payload.update(overrides)
    return DreamAnalysisV1.model_validate(payload)


def test_legacy_mapper_v1_maps_interpretation_and_themes():
    legacy = LegacyMapperV1().map(_canonical())

    assert legacy.interpretation == "Сон может отражать внутреннее напряжение."
    assert "water" in legacy.themes
    assert "shadow" in legacy.themes
    assert legacy.questions_for_user == ["Что осталось самым ярким после пробуждения?"]


def test_legacy_mapper_v1_falls_back_to_summary():
    legacy = LegacyMapperV1().map(_canonical(narrative_interpretation=""))

    assert legacy.interpretation == "Краткое резюме сна."


def test_legacy_mapper_v1_deduplicates_themes():
    legacy = LegacyMapperV1().map(
        _canonical(
            symbols=[
                {
                    "symbol": "shadow",
                    "meaning": "может указывать на скрытые части",
                    "emotional_charge": "напряжённая",
                }
            ],
            jungian_interpretation={
                "archetypes": ["shadow"],
                "shadow_elements": [],
                "anima_animus_signals": [],
                "individuation_hint": "hint",
            },
        )
    )

    assert legacy.themes.count("shadow") == 1
