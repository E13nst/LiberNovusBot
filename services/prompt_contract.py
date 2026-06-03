"""Compatibility exports for the prompt contract API.

Runtime prompt ownership lives in ``services.prompts``. Keep this module so
existing call sites can migrate gradually without changing behavior.
"""

# project
from services.prompts.contracts import (
    DEFAULT_PROMPT_CONTRACT,
    FIXED_ANALYSIS_INSTRUCTIONS,
    FIXED_ANALYTICAL_FRAMEWORK,
    FIXED_OUTPUT_FORMAT,
    JUNGIAN_PROMPT_CONTRACT_V1,
    JUNGIAN_PROMPT_CONTRACT_V2,
    PROMPT_PREFIX,
    PROMPT_PREFIX_V1,
    PROMPT_PREFIX_V2,
    PromptContract,
    SectionFieldSpec,
    SectionSpec,
    get_fixed_analysis_instructions,
    get_fixed_analytical_framework,
    get_fixed_output_format,
)

__all__ = [
    "DEFAULT_PROMPT_CONTRACT",
    "FIXED_ANALYSIS_INSTRUCTIONS",
    "FIXED_ANALYTICAL_FRAMEWORK",
    "FIXED_OUTPUT_FORMAT",
    "JUNGIAN_PROMPT_CONTRACT_V1",
    "JUNGIAN_PROMPT_CONTRACT_V2",
    "PROMPT_PREFIX",
    "PROMPT_PREFIX_V1",
    "PROMPT_PREFIX_V2",
    "PromptContract",
    "SectionFieldSpec",
    "SectionSpec",
    "get_fixed_analysis_instructions",
    "get_fixed_analytical_framework",
    "get_fixed_output_format",
]
