# stdlib
import re

# thirdparty
from pydantic import BaseModel, ConfigDict

# project
from services.analysis.schema.dream_analysis_v1 import DreamAnalysisV1

_REPLACEMENTS = (
    (r"\bэто значит\b", "это может быть связано с"),
    (r"\bозначает\b", "может быть связано с"),
    (r"\bсимволизирует\b", "может быть связано с"),
    (r"\bдоказывает\b", "может указывать на"),
    (r"\bуказывает на\b", "может быть связано с"),
    (r"\bглавный смысл сна\b", "один из возможных ракурсов"),
    (r"\bосновное значение\b", "один из возможных ракурсов"),
)


class DreamReflectionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dream_structure: list[str]
    reflection_directions: list[str]
    questions: list[str]
    dream_context: list[str]


class DreamReflectionTransformer:
    """Convert canonical analysis payload into non-authoritative reflection response."""

    def transform(self, canonical: DreamAnalysisV1) -> DreamReflectionResponse:
        return DreamReflectionResponse(
            dream_structure=self._build_structure(canonical),
            reflection_directions=self._build_directions(canonical),
            questions=self._build_questions(canonical),
            dream_context=self._build_context(canonical),
        )

    def _build_structure(self, canonical: DreamAnalysisV1) -> list[str]:
        lines: list[str] = []
        summary = self._sanitize_text(canonical.summary)
        if summary:
            lines.append(f"- Ключевые образы и сцены: {summary}")

        if canonical.symbols:
            symbol_names = ", ".join(item.symbol for item in canonical.symbols if item.symbol.strip())
            if symbol_names:
                lines.append(f"- Отмеченные образы: {symbol_names}.")

        emotional_primary = canonical.emotional_state.primary.strip()
        emotional_secondary = canonical.emotional_state.secondary.strip()
        if emotional_primary:
            if emotional_secondary:
                lines.append(
                    f"- Эмоциональный фон: {emotional_primary}; рядом может звучать {emotional_secondary}."
                )
            else:
                lines.append(f"- Эмоциональный фон: {emotional_primary}.")

        archetypes = [name.strip() for name in canonical.jungian_interpretation.archetypes if name.strip()]
        if archetypes:
            lines.append(f"- Отмеченные мотивы в записи: {', '.join(archetypes)}.")

        return lines or ["- В текущей записи пока недостаточно структурных деталей для вывода."]

    def _build_directions(self, canonical: DreamAnalysisV1) -> list[str]:
        candidates: list[str] = []
        for text in (
            canonical.narrative_interpretation,
            canonical.key_insight,
            canonical.jungian_interpretation.individuation_hint,
            *(item.meaning for item in canonical.symbols),
        ):
            sanitized = self._sanitize_text(text)
            if sanitized:
                candidates.append(sanitized)

        directions: list[str] = []
        for idx, item in enumerate(candidates[:3]):
            if idx == 0:
                directions.append(f"- Можно рассмотреть: {item}")
            elif idx == 1:
                directions.append(f"- Может быть связано с тем, что: {item}")
            else:
                directions.append(f"- Иногда такие образы появляются когда: {item}")

        if not directions:
            directions = [
                "- Можно рассмотреть, какие переживания в этом сне кажутся наиболее живыми.",
                "- Может быть связано с текущими внутренними противоречиями, если это откликается.",
            ]
        return directions

    def _build_questions(self, canonical: DreamAnalysisV1) -> list[str]:
        questions: list[str] = []
        for note in canonical.uncertainty_notes:
            question = self._as_question(self._sanitize_text(note))
            if question:
                questions.append(question)

        symbol = ""
        if canonical.symbols:
            symbol = canonical.symbols[0].symbol.strip()

        fallback_pool = [
            "Что в этом сне сейчас откликается сильнее всего?",
            "Какая часть сна вызывает больше напряжения или интереса?",
            (
                f"С чем у вас сейчас может ассоциироваться образ «{symbol}»?"
                if symbol
                else "Какие образы из сна хочется исследовать дальше?"
            ),
            "Какой вопрос к себе хочется оставить открытым после этого сна?",
        ]

        for fallback in fallback_pool:
            if len(questions) >= 4:
                break
            if len(questions) >= 2 and canonical.uncertainty_notes:
                break
            questions.append(fallback)

        return questions[:4]

    def _build_context(self, canonical: DreamAnalysisV1) -> list[str]:
        _ = canonical
        # Context in #023 is projection-only: no DB lookup and no cross-dream inference.
        return ["- Пока нет сохранённых повторяющихся мотивов в этой сессии."]

    def _sanitize_text(self, text: str) -> str:
        result = text.strip()
        if not result:
            return ""
        for pattern, replacement in _REPLACEMENTS:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        return re.sub(r"\s+", " ", result).strip()

    def _as_question(self, text: str) -> str:
        value = text.strip().rstrip(".!")
        if not value:
            return ""
        if not value.endswith("?"):
            value = f"{value}?"
        return value
