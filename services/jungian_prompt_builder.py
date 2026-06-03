# stdlib
from datetime import datetime

# project
from db.models.dream_model import Dream
from db.models.session_summary_model import SessionSummary
from services.prompts.compiler import (
    CompiledJungianPrompt,
    compile_jungian_prompt,
    render_compiled_prompt,
)
from services.prompts.contracts import JUNGIAN_PROMPT_CONTRACT_V2, PROMPT_PREFIX

__all__ = [
    "PROMPT_PREFIX",
    "CompiledJungianPrompt",
    "build_jungian_prompt",
    "compile_jungian_prompt",
    "render_compiled_prompt",
]


def build_jungian_prompt(
    session_summary: SessionSummary,
    dreams: list[Dream],
    *,
    last_activity_at: datetime | None = None,
    session_created_at: datetime | None = None,
) -> str:
    """Build a deterministic, hallucination-safe Jungian analysis prompt."""
    compiled = compile_jungian_prompt(
        session_summary,
        dreams,
        last_activity_at=last_activity_at,
        session_created_at=session_created_at,
    )
    return render_compiled_prompt(compiled, JUNGIAN_PROMPT_CONTRACT_V2)
