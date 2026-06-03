from pathlib import Path

import pytest

from services.prompts.registry import PromptId, get_prompt_registry

pytestmark = pytest.mark.unit


def test_prompt_registry_exposes_required_runtime_assets():
    registry = get_prompt_registry()

    required = [
        PromptId(prompt_type="dialogue", version="v1", language="ru", name="companion_style_anchor"),
        PromptId(prompt_type="dialogue", version="v1", language="ru", name="dialogue_turn"),
        PromptId(prompt_type="reflection", version="v2", language="ru", name="dream_analysis"),
        PromptId(prompt_type="fixed", version="v1", language="ru", name="clarification"),
        PromptId(prompt_type="fixed", version="v1", language="ru", name="session_continue"),
        PromptId(prompt_type="fixed", version="v1", language="ru", name="safety"),
    ]

    for prompt_id in required:
        asset = registry.get(prompt_id)
        assert asset.prompt_id == prompt_id
        assert asset.path.suffix == ".md"
        assert asset.path.is_file()
        assert asset.content.strip()


def test_prompt_registry_does_not_use_root_prompt_txt():
    registry = get_prompt_registry()
    asset = registry.get(
        PromptId(prompt_type="dialogue", version="v1", language="ru", name="companion_style_anchor")
    )

    assert asset.path.name == "companion_style_anchor_ru.md"
    assert asset.path != Path(__file__).resolve().parents[3] / "prompt.txt"
