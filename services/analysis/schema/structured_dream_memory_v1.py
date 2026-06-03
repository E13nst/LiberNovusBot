# thirdparty
from pydantic import BaseModel, ConfigDict, Field


class DreamFigureV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    role_hint: str = ""
    emotional_charge: str = ""


class AmplificationCandidateV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    personal: str = ""
    cultural: str = ""
    archetypal: str = ""


class StructuredDreamMemoryV1(BaseModel):
    """Background dream-scoped memory aligned with Hall/Jung exploration stages."""

    model_config = ConfigDict(extra="forbid")

    dream_details: list[str] = Field(default_factory=list)
    dream_ego_activity: list[str] = Field(default_factory=list)
    figures: list[DreamFigureV1] = Field(default_factory=list)
    emotional_field: list[str] = Field(default_factory=list)
    personal_context_questions: list[str] = Field(default_factory=list)
    amplification_candidates: list[AmplificationCandidateV1] = Field(default_factory=list)
    compensation_hypotheses: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    recurring_motifs: list[str] = Field(default_factory=list)
    uncertainty_notes: list[str] = Field(default_factory=list)
