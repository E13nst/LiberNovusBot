# thirdparty
from pydantic import ValidationError

# project
from services.analysis.schema.dream_analysis_v1 import DreamAnalysisV1

DEFAULT_PROMPT_VERSION = "v2"


class AnalysisValidationError(ValueError):
    """Raised when provider output does not match the analysis contract."""


def validate_analysis_output(payload: dict) -> DreamAnalysisV1:
    """Strictly validate provider JSON against DreamAnalysisV1."""
    try:
        return DreamAnalysisV1.model_validate(payload)
    except ValidationError as exc:
        raise AnalysisValidationError(str(exc)) from exc
