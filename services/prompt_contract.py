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
    forbidden_phrases: tuple[str, ...]
    placeholder_pattern: Pattern[str]


PROMPT_PREFIX = "[CONTROLLED JUNGIAN PROMPT v1]"

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

JUNGIAN_PROMPT_CONTRACT_V1 = PromptContract(
    version="v1",
    prefix=PROMPT_PREFIX,
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

# Fixed body text owned by the contract (sections 4–5).
FIXED_ANALYSIS_INSTRUCTIONS: tuple[str, ...] = _ANALYSIS_INSTRUCTIONS
FIXED_ANALYTICAL_FRAMEWORK: tuple[str, ...] = _ANALYTICAL_FRAMEWORK
FIXED_OUTPUT_FORMAT: tuple[str, ...] = _OUTPUT_FORMAT
