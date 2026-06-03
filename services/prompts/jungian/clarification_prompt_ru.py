# project
from services.prompts.assets import load_prompt_asset_text
from services.prompts.registry import PromptId

_CLARIFICATION_PROMPT = PromptId("fixed", "v1", "ru", "clarification")
_SESSION_CONTINUE_PROMPT = PromptId("fixed", "v1", "ru", "session_continue")

CLARIFICATION_RESPONSE_RU = load_prompt_asset_text(_CLARIFICATION_PROMPT)
SESSION_CONTINUE_RESPONSE_RU = load_prompt_asset_text(_SESSION_CONTINUE_PROMPT)


def build_clarification_response() -> str:
    return CLARIFICATION_RESPONSE_RU


def build_session_continue_response() -> str:
    return SESSION_CONTINUE_RESPONSE_RU

