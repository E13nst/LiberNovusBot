# project
from services.prompts.assets import load_prompt_asset_text
from services.prompts.registry import PromptId

_SAFETY_PROMPT = PromptId("fixed", "v1", "ru", "safety")

SAFETY_RESPONSE_RU = load_prompt_asset_text(_SAFETY_PROMPT)


def build_safety_response() -> str:
    return SAFETY_RESPONSE_RU
