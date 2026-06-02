# project
from services.analysis.schema.dream_analysis_v1 import DreamAnalysisV1
from services.reflection.dream_reflection_transformer import DreamReflectionTransformer
from tests.fixtures.dream_analysis_v1 import sample_dream_analysis_v1_json


def _canonical(**overrides) -> DreamAnalysisV1:
    payload = sample_dream_analysis_v1_json()
    payload.update(overrides)
    return DreamAnalysisV1.model_validate(payload)


def _combined_text(lines: list[str]) -> str:
    return "\n".join(lines).lower()


def test_no_authoritative_interpretation():
    canonical = _canonical(
        summary="Этот сон означает внутренний конфликт.",
        narrative_interpretation="Образ воды символизирует тревогу и доказывает подавленные эмоции.",
        key_insight="Это указывает на факт непрожитого страха.",
    )

    reflection = DreamReflectionTransformer().transform(canonical)
    text = _combined_text(
        reflection.dream_structure
        + reflection.reflection_directions
        + reflection.questions
        + reflection.dream_context
    )

    for forbidden in ("означает", "символизирует", "доказывает"):
        assert forbidden not in text


def test_questions_always_present():
    canonical = _canonical(uncertainty_notes=[])

    reflection = DreamReflectionTransformer().transform(canonical)

    assert 2 <= len(reflection.questions) <= 4
    assert all(item.endswith("?") for item in reflection.questions)


def test_no_meaning_closure():
    canonical = _canonical(
        key_insight="Главный смысл сна в том, что нужно отказаться от контроля.",
        narrative_interpretation="Основное значение сна связано с подавлением чувств.",
    )

    reflection = DreamReflectionTransformer().transform(canonical)
    text = _combined_text(reflection.reflection_directions + reflection.dream_context)

    assert "главный смысл сна" not in text
    assert "основное значение" not in text


def test_reflection_not_interpretation():
    canonical = _canonical(uncertainty_notes=[])

    reflection = DreamReflectionTransformer().transform(canonical)

    assert reflection.reflection_directions
    merged = _combined_text(reflection.reflection_directions)
    assert any(marker in merged for marker in ("может", "можно", "иногда"))


def test_no_cross_dream_memory_inference():
    canonical = _canonical(uncertainty_notes=["Что в этом сне кажется наиболее важным сейчас?"])

    reflection = DreamReflectionTransformer().transform(canonical)
    text = _combined_text(
        reflection.dream_structure
        + reflection.reflection_directions
        + reflection.questions
        + reflection.dream_context
    )

    forbidden_phrases = (
        "earlier dreams",
        "previous entries suggest",
        "you often dream",
        "в прошлых снах",
        "ранее в сновидениях",
        "ты часто видишь",
    )
    assert all(phrase not in text for phrase in forbidden_phrases)
