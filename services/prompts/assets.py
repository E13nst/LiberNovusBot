# stdlib
from pathlib import Path

# project
from services.prompts.registry import PromptId, get_prompt_registry


class PromptAssetNotFound(FileNotFoundError):
    pass


def load_prompt_asset_text(prompt_id: PromptId) -> str:
    registry = get_prompt_registry()
    try:
        path = registry.path_for(prompt_id)
    except KeyError as exc:
        raise PromptAssetNotFound(str(exc)) from exc
    return _read_prompt_asset(prompt_id, path)


def _read_prompt_asset(prompt_id: PromptId, path: Path) -> str:
    if not path.is_file():
        raise PromptAssetNotFound(f"Prompt asset file is missing for {prompt_id}: {path}")
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        raise PromptAssetNotFound(f"Prompt asset file is empty for {prompt_id}: {path}")
    return content
