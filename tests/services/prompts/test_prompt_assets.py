import pytest

from services.prompts.assets import PromptAssetNotFound, load_prompt_asset_text
from services.prompts.registry import PromptId

pytestmark = pytest.mark.unit


def test_load_prompt_asset_reads_utf8_markdown():
    content = load_prompt_asset_text(
        PromptId(prompt_type="fixed", version="v1", language="ru", name="clarification")
    )

    assert "Похоже" in content
    assert "опишите сон" in content


def test_load_prompt_asset_missing_asset_raises_clear_error():
    with pytest.raises(PromptAssetNotFound) as exc_info:
        load_prompt_asset_text(
            PromptId(prompt_type="fixed", version="v1", language="ru", name="missing")
        )

    assert "fixed" in str(exc_info.value)
    assert "missing" in str(exc_info.value)
