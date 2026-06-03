# stdlib
from dataclasses import dataclass
from pathlib import Path

_ASSET_ROOT = Path(__file__).resolve().parent / "assets"


@dataclass(frozen=True)
class PromptId:
    prompt_type: str
    version: str
    language: str
    name: str


@dataclass(frozen=True)
class PromptAsset:
    prompt_id: PromptId
    path: Path
    content: str


class PromptRegistry:
    def __init__(self, mapping: dict[PromptId, Path]) -> None:
        self._mapping = dict(mapping)

    def get(self, prompt_id: PromptId) -> PromptAsset:
        path = self.path_for(prompt_id)
        return PromptAsset(
            prompt_id=prompt_id,
            path=path,
            content=path.read_text(encoding="utf-8").strip(),
        )

    def path_for(self, prompt_id: PromptId) -> Path:
        try:
            return self._mapping[prompt_id]
        except KeyError as exc:
            raise KeyError(f"Prompt asset is not registered: {prompt_id}") from exc


def _build_registry() -> PromptRegistry:
    return PromptRegistry(
        {
            PromptId("dialogue", "v1", "ru", "companion_style_anchor"): (
                _ASSET_ROOT / "dialogue" / "companion_style_anchor_ru.md"
            ),
            PromptId("dialogue", "v1", "ru", "dialogue_turn"): (
                _ASSET_ROOT / "dialogue" / "dialogue_turn_v1_ru.md"
            ),
            PromptId("reflection", "v2", "ru", "dream_analysis"): (
                _ASSET_ROOT / "reflection" / "dream_analysis_v2_ru.md"
            ),
            PromptId("fixed", "v1", "ru", "clarification"): (
                _ASSET_ROOT / "fixed" / "clarification_ru.md"
            ),
            PromptId("fixed", "v1", "ru", "session_continue"): (
                _ASSET_ROOT / "fixed" / "session_continue_ru.md"
            ),
            PromptId("fixed", "v1", "ru", "safety"): (
                _ASSET_ROOT / "fixed" / "safety_ru.md"
            ),
        }
    )


_REGISTRY = _build_registry()


def get_prompt_registry() -> PromptRegistry:
    return _REGISTRY
