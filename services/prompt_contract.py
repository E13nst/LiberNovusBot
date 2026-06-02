# stdlib
import re
from dataclasses import dataclass
from re import Pattern


@dataclass(frozen=True)
class SectionFieldSpec:
    """A single allowed field line inside a contract section."""

    name: str
    required: bool = True


@dataclass(frozen=True)
class SectionSpec:
    """One ordered section in the Jungian prompt DSL."""

    number: int
    heading: str
    fields: tuple[SectionFieldSpec, ...] = ()
    dream_entry: bool = False


@dataclass(frozen=True)
class PromptContract:
    """Strict schema for a versioned Jungian LLM-input prompt."""

    version: str
    prefix: str
    sections: tuple[SectionSpec, ...]
    required_instruction_anchors: tuple[str, ...]
    required_framework_items: tuple[str, ...]
    required_instruction_lines: tuple[str, ...]
    required_output_format_lines: tuple[str, ...]
    forbidden_phrases: tuple[str, ...]
    placeholder_pattern: Pattern[str]


PROMPT_PREFIX_V1 = "[CONTROLLED JUNGIAN PROMPT v1]"
PROMPT_PREFIX_V2 = "[CONTROLLED JUNGIAN PROMPT v2]"
PROMPT_PREFIX = PROMPT_PREFIX_V2

_ANALYSIS_INSTRUCTIONS = (
    "You are a Jungian analyst.",
    "",
    "Rules:",
    "- Use ONLY provided data",
    "- Do NOT invent facts",
    "- Do NOT assume missing context",
    "- Do NOT generate new dream content",
    "- Do NOT infer user life facts not present in the input",
    "- Treat all dream elements as subjective psychic material",
    "- Each interpretation must reference specific dream fragments",
    '- If information is missing, respond with "insufficient data"',
    "- If ambiguity exists, explicitly state it",
    '- Prefer "possible indicates" / "may suggest" over absolute statements',
    "- Avoid absolute statements",
    "- Always respond in Russian language.",
    "- Be critically reflective about your output.",
    "- Verify consistency with the provided architecture and data constraints.",
    "- Do not invent information not present in input data.",
    "- Prefer uncertainty over hallucination.",
)

_ANALYTICAL_FRAMEWORK = (
    "Respond using exactly this structure:",
    "1. Key motifs",
    "2. Emotional tone patterns",
    "3. Repeating symbols",
    "4. Possible archetypal themes (optional, only if strongly supported)",
    "5. Psychological tension / conflict",
    "6. Questions for further exploration",
)

_OUTPUT_FORMAT = (
    "Dream Interpretation Mode: you are an analytical module, not a chat assistant.",
    "Return a single JSON object only. No markdown fences and no text outside the JSON object.",
    "Do not return prose-only answers.",
    "Required JSON keys:",
    '- "summary": string',
    '- "symbols": list of {"symbol": string, "meaning": string, "emotional_charge": string}',
    '- "emotional_state": {"primary": string, "secondary": string, "intensity": number 0-1}',
    '- "jungian_interpretation": {"archetypes": list of strings, "shadow_elements": list of strings, "anima_animus_signals": list of strings, "individuation_hint": string}',
    '- "narrative_interpretation": string',
    '- "key_insight": string',
    '- "uncertainty_notes": list of strings',
    "All JSON string values must be in Russian.",
    "Provide structural psycho-interpretation grounded only in provided dream data.",
    "If information is missing, use uncertainty_notes instead of inventing facts.",
)

_ANALYSIS_INSTRUCTIONS_V2_RU = (
    "Вы — аналитический модуль юнгианской рефлексии.",
    "",
    "Правила:",
    "- Используйте только данные из текущего ввода.",
    "- Не добавляйте факты, которых нет в материале сна.",
    "- Сон не имеет фиксированного значения.",
    "- Мы исследуем, а не интерпретируем окончательно.",
    "- Формулируйте только возможные гипотезы.",
    "- Вопросы важнее выводов.",
    "- Не используйте утверждения типа «это означает».",
    "- Не используйте фразы «ваш сон говорит» и диагностический стиль.",
    "- При нехватке данных фиксируйте неопределенность в uncertainty_notes.",
    "- Все текстовые значения в ответе должны быть на русском языке.",
)

_ANALYTICAL_FRAMEWORK_V2_RU = (
    "Используйте эту структуру анализа:",
    "1. Ключевые мотивы и образы",
    "2. Эмоциональный тон и динамика",
    "3. Повторяющиеся символы",
    "4. Возможные архетипические гипотезы (1-3, только при опоре на материал)",
    "5. Внутренние напряжения / конфликт",
    "6. Открытые вопросы для дальнейшего исследования",
)

_OUTPUT_FORMAT_V2_RU = (
    "Режим анализа сновидения: вы аналитический модуль, а не чат-ассистент.",
    "Верните только один JSON-объект. Без markdown и без текста вне JSON.",
    "Не возвращайте ответ в виде свободного эссе без JSON.",
    "Обязательные JSON-ключи:",
    '- "summary": string',
    '- "symbols": list of {"symbol": string, "meaning": string, "emotional_charge": string}',
    '- "emotional_state": {"primary": string, "secondary": string, "intensity": number 0-1}',
    '- "jungian_interpretation": {"archetypes": list of strings, "shadow_elements": list of strings, "anima_animus_signals": list of strings, "individuation_hint": string}',
    '- "narrative_interpretation": string',
    '- "key_insight": string',
    '- "uncertainty_notes": list of strings',
    "Все строковые значения JSON должны быть на русском языке.",
    "Опирайтесь только на предоставленный материал сна.",
    "Если данных недостаточно, заполняйте uncertainty_notes вместо домысливания.",
)

JUNGIAN_PROMPT_CONTRACT_V1 = PromptContract(
    version="v1",
    prefix=PROMPT_PREFIX_V1,
    sections=(
        SectionSpec(
            number=1,
            heading="## 1. CONTEXT BLOCK (FACTS ONLY)",
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
            heading="## 2. DREAM LOG (VERBATIM REDUCED FORM)",
            dream_entry=True,
        ),
        SectionSpec(
            number=3,
            heading="## 3. SESSION SUMMARY BLOCK (STRUCTURED DATA)",
            fields=(
                SectionFieldSpec("key_symbols"),
                SectionFieldSpec("recurring_words"),
                SectionFieldSpec("raw_text_sample"),
            ),
        ),
        SectionSpec(
            number=4,
            heading="## 4. ANALYSIS INSTRUCTIONS (CRITICAL PART)",
        ),
        SectionSpec(
            number=5,
            heading="## 5. ANALYTICAL FRAMEWORK (FIXED STRUCTURE)",
        ),
        SectionSpec(
            number=6,
            heading="## 6. OUTPUT FORMAT (JSON ONLY)",
        ),
    ),
    required_instruction_anchors=(
        "only provided data",
        "do not invent facts",
        "insufficient data",
        "possible indicates",
        "may suggest",
        "russian language",
        "uncertainty over hallucination",
    ),
    required_framework_items=_ANALYTICAL_FRAMEWORK[1:],
    required_instruction_lines=("You are a Jungian analyst.", "Rules:", "- Use ONLY provided data"),
    required_output_format_lines=("Return a single JSON object only.", "Required JSON keys:"),
    forbidden_phrases=(
        "i don't know but",
        "probably the user",
        "let me guess",
        "you may assume",
        "feel free to imagine",
        "fill in the gaps",
    ),
    placeholder_pattern=re.compile(r"\[(FILL|MISSING)", re.IGNORECASE),
)

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
        SectionSpec(
            number=4,
            heading="## 4. ПРАВИЛА РЕФЛЕКСИИ",
        ),
        SectionSpec(
            number=5,
            heading="## 5. АНАЛИТИЧЕСКИЙ ФОКУС",
        ),
        SectionSpec(
            number=6,
            heading="## 6. ФОРМАТ ОТВЕТА (JSON)",
        ),
    ),
    required_instruction_anchors=(
        "сон не имеет фиксированного значения",
        "мы исследуем, а не интерпретируем окончательно",
        "возможные гипотезы",
        "вопросы важнее выводов",
        "не используйте утверждения типа «это означает»",
    ),
    required_framework_items=_ANALYTICAL_FRAMEWORK_V2_RU[1:],
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


def get_fixed_analysis_instructions(contract: PromptContract) -> tuple[str, ...]:
    if contract.version == "v2":
        return _ANALYSIS_INSTRUCTIONS_V2_RU
    return _ANALYSIS_INSTRUCTIONS


def get_fixed_analytical_framework(contract: PromptContract) -> tuple[str, ...]:
    if contract.version == "v2":
        return _ANALYTICAL_FRAMEWORK_V2_RU
    return _ANALYTICAL_FRAMEWORK


def get_fixed_output_format(contract: PromptContract) -> tuple[str, ...]:
    if contract.version == "v2":
        return _OUTPUT_FORMAT_V2_RU
    return _OUTPUT_FORMAT

# Fixed body text owned by the contract (sections 4–5).
FIXED_ANALYSIS_INSTRUCTIONS: tuple[str, ...] = get_fixed_analysis_instructions(DEFAULT_PROMPT_CONTRACT)
FIXED_ANALYTICAL_FRAMEWORK: tuple[str, ...] = get_fixed_analytical_framework(DEFAULT_PROMPT_CONTRACT)
FIXED_OUTPUT_FORMAT: tuple[str, ...] = get_fixed_output_format(DEFAULT_PROMPT_CONTRACT)
