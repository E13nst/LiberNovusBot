# stdlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

# project
from db.models.dream_model import Dream
from db.models.session_summary_model import SessionSummary
from services.prompts.contracts import (
    DEFAULT_PROMPT_CONTRACT,
    PromptContract,
    get_fixed_analysis_instructions,
    get_fixed_analytical_framework,
    get_fixed_output_format,
)

_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


@dataclass(frozen=True)
class ContextBlock:
    session_id: UUID
    user_id: int
    dream_count: int
    session_duration: str
    last_activity_at: str


@dataclass(frozen=True)
class DreamEntry:
    index: int
    text: str
    timestamp: str


@dataclass(frozen=True)
class SessionSummaryBlock:
    key_symbols: list[str]
    recurring_words: list[str]
    raw_text_sample: str


@dataclass(frozen=True)
class CompiledJungianPrompt:
    """Intermediate representation (IR) for the Jungian prompt DSL."""

    context: ContextBlock
    dreams: tuple[DreamEntry, ...]
    summary: SessionSummaryBlock


def _format_datetime(value: datetime | None) -> str:
    if value is None:
        return "N/A"
    return value.strftime(_DATETIME_FORMAT)


def _format_duration(duration: timedelta | None) -> str:
    if duration is None:
        return "N/A"
    total_seconds = int(duration.total_seconds())
    if total_seconds < 0:
        return "N/A"
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"


def _format_list(values: list[str]) -> str:
    if not values:
        return "[]"
    return "[" + ", ".join(values) + "]"


def _sort_dreams(dreams: list[Dream]) -> list[Dream]:
    return sorted(dreams, key=lambda dream: (dream.created_at, dream.id))


def compile_jungian_prompt(
    session_summary: SessionSummary,
    dreams: list[Dream],
    *,
    last_activity_at: datetime | None = None,
    session_created_at: datetime | None = None,
) -> CompiledJungianPrompt:
    """Compile DB models into contract-conformant prompt IR."""
    session_duration: timedelta | None = None
    if last_activity_at is not None and session_created_at is not None:
        session_duration = last_activity_at - session_created_at

    dream_entries = tuple(
        DreamEntry(
            index=index,
            text=dream.text,
            timestamp=_format_datetime(dream.created_at),
        )
        for index, dream in enumerate(_sort_dreams(dreams), start=1)
    )

    raw_sample = session_summary.raw_text_sample
    return CompiledJungianPrompt(
        context=ContextBlock(
            session_id=session_summary.session_id,
            user_id=session_summary.user_id,
            dream_count=session_summary.dream_count,
            session_duration=_format_duration(session_duration),
            last_activity_at=_format_datetime(last_activity_at),
        ),
        dreams=dream_entries,
        summary=SessionSummaryBlock(
            key_symbols=list(session_summary.key_symbols),
            recurring_words=list(session_summary.recurring_words),
            raw_text_sample=raw_sample if raw_sample is not None else "N/A",
        ),
    )


def render_compiled_prompt(
    compiled: CompiledJungianPrompt,
    contract: PromptContract = DEFAULT_PROMPT_CONTRACT,
) -> str:
    """Serialize IR into the deterministic prompt string defined by the contract."""
    sections: list[str] = [
        contract.prefix,
        "",
        contract.sections[0].heading,
        f"session_id: {compiled.context.session_id}",
        f"user_id: {compiled.context.user_id}",
        f"dream_count: {compiled.context.dream_count}",
        f"session_duration: {compiled.context.session_duration}",
        f"last_activity_at: {compiled.context.last_activity_at}",
        "",
        contract.sections[1].heading,
    ]

    if not compiled.dreams:
        sections.append("(no dreams provided)")
    else:
        for entry in compiled.dreams:
            sections.extend(
                [
                    f"[DREAM {entry.index}]",
                    f"text: {entry.text}",
                    f"timestamp: {entry.timestamp}",
                    "",
                ]
            )

    sections.extend(
        [
            contract.sections[2].heading,
            f"key_symbols: {_format_list(compiled.summary.key_symbols)}",
            f"recurring_words: {_format_list(compiled.summary.recurring_words)}",
            f"raw_text_sample: {compiled.summary.raw_text_sample}",
            "",
            contract.sections[3].heading,
            *get_fixed_analysis_instructions(contract),
            "",
            contract.sections[4].heading,
            *get_fixed_analytical_framework(contract),
            "",
            contract.sections[5].heading,
            *get_fixed_output_format(contract),
        ]
    )

    return "\n".join(sections)
