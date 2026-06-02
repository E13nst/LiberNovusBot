# thirdparty
from pydantic import BaseModel, ConfigDict, Field, model_validator


class DreamSymbolV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    meaning: str
    emotional_charge: str


class EmotionalStateV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary: str
    secondary: str
    intensity: float = Field(ge=0.0, le=1.0)


class JungianInterpretationV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    archetypes: list[str]
    shadow_elements: list[str]
    anima_animus_signals: list[str]
    individuation_hint: str


class DreamAnalysisV1(BaseModel):
    """Canonical dream analysis contract for #021."""

    model_config = ConfigDict(extra="forbid")

    summary: str
    symbols: list[DreamSymbolV1]
    emotional_state: EmotionalStateV1
    jungian_interpretation: JungianInterpretationV1
    narrative_interpretation: str
    key_insight: str
    uncertainty_notes: list[str]

    @model_validator(mode="after")
    def _symbols_required_when_interpretation_exists(self) -> "DreamAnalysisV1":
        has_interpretation = bool(
            self.narrative_interpretation.strip() or self.key_insight.strip()
        )
        if has_interpretation and not self.symbols:
            raise ValueError("symbols must be non-empty when interpretation content is present")
        return self
