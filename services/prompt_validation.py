"""Compatibility exports for prompt validation."""

# project
from services.prompts.validation import (
    StructuralValidationError,
    validate_prompt_safety,
    validate_prompt_structure,
)

__all__ = [
    "StructuralValidationError",
    "validate_prompt_safety",
    "validate_prompt_structure",
]
