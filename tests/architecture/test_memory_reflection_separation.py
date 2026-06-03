# stdlib
import ast
from pathlib import Path

# thirdparty
import pytest

pytestmark = pytest.mark.unit

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _imports_for(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def _assert_no_prefix(imports: set[str], forbidden_prefixes: tuple[str, ...]) -> None:
    for item in imports:
        assert not item.startswith(forbidden_prefixes), f"Forbidden dependency detected: {item}"


def test_memory_modules_do_not_depend_on_reflection_or_dialogue_modules():
    memory_files = [
        PROJECT_ROOT / "services/memory/memory_extractor.py",
        PROJECT_ROOT / "services/memory/memory_prompt_builder.py",
        PROJECT_ROOT / "services/memory/memory_orchestrator.py",
    ]
    forbidden = (
        "services.analysis_orchestrator",
        "services.jungian_prompt_builder",
        "services.analysis.schema.dream_analysis_v1",
        "services.prompts.jungian",
        "services.dialogue",
    )
    for file_path in memory_files:
        _assert_no_prefix(_imports_for(file_path), forbidden)


def test_reflection_pipeline_does_not_depend_on_memory_builder():
    reflection_files = [
        PROJECT_ROOT / "services/analysis_orchestrator.py",
        PROJECT_ROOT / "services/jungian_prompt_builder.py",
        PROJECT_ROOT / "services/prompts/jungian/reflection_prompt_v2_ru.py",
    ]
    forbidden = (
        "services.memory.memory_prompt_builder",
        "services.memory.memory_extractor",
    )
    for file_path in reflection_files:
        _assert_no_prefix(_imports_for(file_path), forbidden)


def test_dialogue_layer_does_not_depend_on_memory_extractor_or_reflection_runtime():
    dialogue_files = [
        PROJECT_ROOT / "services/dialogue/dialogue_orchestrator.py",
        PROJECT_ROOT / "services/dialogue/dialogue_prompt.py",
    ]
    forbidden = (
        "services.memory.memory_extractor",
        "services.analysis_orchestrator",
    )
    for file_path in dialogue_files:
        _assert_no_prefix(_imports_for(file_path), forbidden)
