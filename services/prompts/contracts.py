# stdlib
import re
from dataclasses import dataclass
from re import Pattern

# project
from services.prompts.assets import load_prompt_asset_text
from services.prompts.registry import PromptId


@dataclass(frozen=True)
class SectionFieldSpec:
    """A single allowed field line inside a prompt contract section."""

    name: str
    required: bool = True


@dataclass(frozen=True)
class SectionSpec:
    """One ordered section in a prompt contract."""

    number: int
    heading: str
    fields: tuple[SectionFieldSpec, ...] = ()
    dream_entry: bool = False


@dataclass(frozen=True)
class PromptContract:
    """Strict schema for a versioned runtime prompt."""

    version: str
    prefix: str
    sections: tuple[SectionSpec, ...]
    required_instruction_anchors: tuple[str, ...]
    required_framework_items: tuple[str, ...]
    required_instruction_lines: tuple[str, ...]
    required_output_format_lines: tuple[str, ...]
    forbidden_phrases: tuple[str, ...]
    placeholder_pattern: Pattern[str]


PROMPT_PREFIX_V2 = "[CONTROLLED JUNGIAN PROMPT v2]"
PROMPT_PREFIX = PROMPT_PREFIX_V2
PROMPT_PREFIX_V1 = "[CONTROLLED JUNGIAN PROMPT v1]"

_REFLECTION_PROMPT_ID = PromptId(
    prompt_type="reflection",
    version="v2",
    language="ru",
    name="dream_analysis",
)


def _extract_markdown_section(markdown: str, heading: str, next_heading: str | None) -> tuple[str, ...]:
    start = markdown.index(heading) + len(heading)
    if next_heading is None:
        body = markdown[start:]
    else:
        body = markdown[start : markdown.index(next_heading, start)]
    return tuple(line for line in body.strip().splitlines())


def _reflection_section_lines(heading: str, next_heading: str | None) -> tuple[str, ...]:
    markdown = load_prompt_asset_text(_REFLECTION_PROMPT_ID)
    return _extract_markdown_section(markdown, heading, next_heading)


JUNGIAN_PROMPT_CONTRACT_V2 = PromptContract(
    version="v2",
    prefix=PROMPT_PREFIX_V2,
    sections=(
        SectionSpec(
            number=1,
            heading="## 1. КОНТЕКСТ СЕССИИ (ФАКТЫ)",
            fields=(
                SectionFieldSpec("session_id"),
                SectionFieldSpec("user_id"),
                SectionFieldSpec("dream_count"),
                SectionFieldSpec("session_duration"),
                SectionFieldSpec("last_activity_at"),
            ),
        ),
        SectionSpec(
            number=2,
            heading="## 2. ЖУРНАЛ СНОВ (ДОСЛОВНО)",
            dream_entry=True,
        ),
        SectionSpec(
            number=3,
            heading="## 3. СВОДКА СЕССИИ (СТРУКТУРА)",
            fields=(
                SectionFieldSpec("key_symbols"),
                SectionFieldSpec("recurring_words"),
                SectionFieldSpec("raw_text_sample"),
            ),
        ),
        SectionSpec(number=4, heading="## 4. ПРАВИЛА РЕФЛЕКСИИ"),
        SectionSpec(number=5, heading="## 5. АНАЛИТИЧЕСКИЙ ФОКУС"),
        SectionSpec(number=6, heading="## 6. ФОРМАТ ОТВЕТА (JSON)"),
    ),
    required_instruction_anchors=(
        "сон не имеет фиксированного значения",
        "мы исследуем, а не интерпретируем окончательно",
        "возможные гипотезы",
        "вопросы важнее выводов",
        "не используйте утверждения типа «это означает»",
    ),
    required_framework_items=(
        "1. Ключевые мотивы и образы",
        "2. Эмоциональный тон и динамика",
        "3. Повторяющиеся символы",
        "4. Возможные архетипические гипотезы (1-3, только при опоре на материал)",
        "5. Внутренние напряжения / конфликт",
        "6. Открытые вопросы для дальнейшего исследования",
    ),
    required_instruction_lines=(
        "Вы — аналитический модуль юнгианской рефлексии.",
        "Правила:",
        "- Сон не имеет фиксированного значения.",
    ),
    required_output_format_lines=("Верните только один JSON-объект.", "Обязательные JSON-ключи:"),
    forbidden_phrases=(
        "это означает, что",
        "ваш сон говорит, что",
        "вы точно",
        "главный смысл сна",
        "основное значение сна",
    ),
    placeholder_pattern=re.compile(r"\[(FILL|MISSING)", re.IGNORECASE),
)

DEFAULT_PROMPT_CONTRACT = JUNGIAN_PROMPT_CONTRACT_V2
JUNGIAN_PROMPT_CONTRACT_V1 = JUNGIAN_PROMPT_CONTRACT_V2


def get_fixed_analysis_instructions(contract: PromptContract) -> tuple[str, ...]:
    return _reflection_section_lines(
        "## 4. ПРАВИЛА РЕФЛЕКСИИ",
        "## 5. АНАЛИТИЧЕСКИЙ ФОКУС",
    )


def get_fixed_analytical_framework(contract: PromptContract) -> tuple[str, ...]:
    return _reflection_section_lines(
        "## 5. АНАЛИТИЧЕСКИЙ ФОКУС",
        "## 6. ФОРМАТ ОТВЕТА (JSON)",
    )


def get_fixed_output_format(contract: PromptContract) -> tuple[str, ...]:
    return _reflection_section_lines("## 6. ФОРМАТ ОТВЕТА (JSON)", None)


FIXED_ANALYSIS_INSTRUCTIONS: tuple[str, ...] = get_fixed_analysis_instructions(DEFAULT_PROMPT_CONTRACT)
FIXED_ANALYTICAL_FRAMEWORK: tuple[str, ...] = get_fixed_analytical_framework(DEFAULT_PROMPT_CONTRACT)
FIXED_OUTPUT_FORMAT: tuple[str, ...] = get_fixed_output_format(DEFAULT_PROMPT_CONTRACT)
