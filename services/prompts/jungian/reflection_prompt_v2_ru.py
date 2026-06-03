# project
from services.prompts.contracts import DEFAULT_PROMPT_CONTRACT, get_fixed_analysis_instructions

REFLECTION_PROMPT_V2_RU = " ".join(get_fixed_analysis_instructions(DEFAULT_PROMPT_CONTRACT))

