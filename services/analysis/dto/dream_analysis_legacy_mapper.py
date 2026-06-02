# thirdparty
from pydantic import BaseModel, ConfigDict

# project
from services.analysis.schema.dream_analysis_v1 import DreamAnalysisV1


class LegacyAnalysisPayload(BaseModel):
    """Presentation-only legacy shape for API/Telegram consumers."""

    model_config = ConfigDict(extra="forbid")

    interpretation: str
    themes: list[str]
    questions_for_user: list[str]


class LegacyMapperV1:
    """Maps canonical DreamAnalysisV1 to legacy presentation fields."""

    def map(self, analysis: DreamAnalysisV1) -> LegacyAnalysisPayload:
        interpretation = analysis.narrative_interpretation.strip() or analysis.summary.strip()
        if not interpretation:
            interpretation = analysis.key_insight.strip()

        themes = [symbol.symbol for symbol in analysis.symbols]
        themes.extend(analysis.jungian_interpretation.archetypes)
        themes = list(dict.fromkeys(themes))

        questions = list(analysis.uncertainty_notes)
        if not questions and analysis.key_insight.strip():
            questions = [analysis.key_insight.strip()]

        return LegacyAnalysisPayload(
            interpretation=interpretation,
            themes=themes,
            questions_for_user=questions,
        )


class LegacyMapperV2:
    """Placeholder for future presentation mapping evolution."""

    def map(self, analysis: DreamAnalysisV1) -> LegacyAnalysisPayload:
        return LegacyMapperV1().map(analysis)
