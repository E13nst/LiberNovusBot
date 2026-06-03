# stdlib
from pathlib import Path
from typing import Iterable

_PROMPT_PATH = Path(__file__).resolve().parent / "memory_extraction_v1_ru.md"

_CORE_FACTUAL_RULES: tuple[str, ...] = (
    "Работайте только с фактами, явно присутствующими в тексте сна.",
    "Если факт не указан напрямую, не добавляйте его.",
    "Не используйте интерпретацию, символические значения и психологические диагнозы.",
)

_MEMORY_SPECIFIC_RULES: tuple[str, ...] = (
    "Извлекайте последовательность событий и участников.",
    "Отмечайте неопределенность только если она явно выражена во входе.",
    "Сохраняйте нейтральный описательный стиль без гипотез о смысле.",
)


def _load_memory_prompt_body() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8").strip()


def build_memory_prompt_rules() -> str:
    lines = ["## Общие правила factual extraction"]
    lines.extend(f"- {item}" for item in _CORE_FACTUAL_RULES)
    lines.append("")
    lines.append("## Специфические правила memory extraction")
    lines.extend(f"- {item}" for item in _MEMORY_SPECIFIC_RULES)
    return "\n".join(lines)


def build_memory_prompt_sections(sections: Iterable[str]) -> str:
    return "\n\n".join(section.strip() for section in sections if section and section.strip())


def build_memory_extraction_instructions() -> str:
    return _load_memory_prompt_body()
