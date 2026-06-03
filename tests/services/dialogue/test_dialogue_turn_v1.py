import pytest

from services.dialogue.schema.dialogue_turn_v1 import DialogueTurnV1

pytestmark = pytest.mark.unit


def test_dialogue_turn_v1_accepts_valid_payload():
    turn = DialogueTurnV1.model_validate(
        {
            "assistant_message": "Спасибо, что поделились. Можно задержаться на том, что сейчас откликается сильнее всего?",
            "focus": ["тревога"],
            "questions": ["Что вы чувствуете при пробуждении?"],
            "background_notes": {},
            "emotional_intensity": 0.7,
            "safety_flags": [],
        }
    )
    assert "Спасибо" in turn.assistant_message


def test_dialogue_turn_v1_coerces_numeric_background_notes():
    turn = DialogueTurnV1.model_validate(
        {
            "assistant_message": "Спасибо, что поделились. Можно задержаться на том, что сейчас откликается сильнее всего?",
            "focus": [],
            "questions": [],
            "background_notes": {"dream_count": 1},
            "emotional_intensity": 0.5,
            "safety_flags": [],
        }
    )
    assert turn.background_notes == {"dream_count": "1"}


def test_dialogue_turn_v1_coerces_mixed_list_background_notes():
    turn = DialogueTurnV1.model_validate(
        {
            "assistant_message": "Спасибо, что поделились. Можно задержаться на том, что сейчас откликается сильнее всего?",
            "focus": [],
            "questions": [],
            "background_notes": {"tags": [1, "exploratory", True]},
            "emotional_intensity": 0.5,
            "safety_flags": [],
        }
    )
    assert turn.background_notes == {"tags": ["1", "exploratory", "true"]}


def test_dialogue_turn_v1_rejects_authoritarian_phrase():
    with pytest.raises(ValueError):
        DialogueTurnV1.model_validate(
            {
                "assistant_message": "Это означает, что вы боитесь потерять контроль над ситуацией в жизни.",
                "focus": [],
                "questions": [],
                "background_notes": {},
                "emotional_intensity": 0.5,
                "safety_flags": [],
            }
        )
