def sample_dream_analysis_v1_json(**overrides) -> dict:
    payload = {
        "summary": "Сон может отражать внутреннее напряжение.",
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
        "narrative_interpretation": "Сон может отражать напряжение между контролем и эмоциями.",
        "key_insight": "Контроль может скрывать уязвимость.",
        "uncertainty_notes": ["Что осталось самым ярким после пробуждения?"],
    }
    payload.update(overrides)
    return payload
