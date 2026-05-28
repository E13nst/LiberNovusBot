# thirdparty
from pydantic import ValidationError

# project
from db.schemas.session_analysis_schema import JungianAnalysisPayloadSchema

ANALYSIS_VERSION = "v1"
DEFAULT_PROMPT_VERSION = "v1"


class AnalysisValidationError(ValueError):
    """Raised when provider output does not match the analysis contract."""


def validate_analysis_output(payload: dict) -> JungianAnalysisPayloadSchema:
    """Strictly validate provider JSON against the canonical analysis schema."""
    try:
        return JungianAnalysisPayloadSchema.model_validate(payload)
    except ValidationError as exc:
        raise AnalysisValidationError(str(exc)) from exc
