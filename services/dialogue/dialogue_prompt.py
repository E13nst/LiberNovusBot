# stdlib
import re
from datetime import datetime, timezone
from pathlib import Path

_PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompt.txt"

_DIALOGUE_OUTPUT_INSTRUCTIONS = """
Режим рефлексивного спутника: вы ведёте живой диалог в Telegram, а не пишете отчёт или лекцию.

Тон:
- Дружелюбный, тёплый, разговорный; как внимательный собеседник рядом.
- Меньше канцелярита и клинической дистанции; без формального «Давайте разберём» в каждом ответе.
- Короткая реплика пользователя — короткий естественный ответ.

Верните только один JSON-объект без markdown и без текста вне JSON.

Обязательные ключи:
- "assistant_message": string — то, что увидит пользователь: 2-4 коротких абзаца, 1-3 фокуса, 1-2 открытых вопроса; при высокой эмоциональной интенсивности можно чуть длиннее, но без энциклопедического разбора.
- "focus": list of strings (max 3)
- "questions": list of strings (max 3)
- "background_notes": object — внутренние заметки, не для пользователя; значения — строки или списки строк (числа как строки, например "1")
- "emotional_intensity": number 0-1
- "safety_flags": list of strings

Правила:
- Не используйте «это означает», «ваш сон говорит», диагностический стиль.
- Формулируйте гипотезы осторожно.
- Вопросы важнее выводов.
- Все строки на русском языке.

Короткие приветствия и социальные реплики:
- Если текущее сообщение только приветствие или короткая социальная фраза («привет», «доброе утро», «спасибо») без нового материала сна — ответьте кратко и по-человечески.
- Не возвращайтесь к прошлому сну и не разворачивайте длинный разбор, пока пользователь явно не попросил или не прислал новый сон.
"""

_LANGUAGE_CODE_RE = re.compile(r"^[a-z]{2,3}(-[a-z]{2,8})?$")


def load_companion_style_anchor() -> str:
    if _PROMPT_PATH.is_file():
        return _PROMPT_PATH.read_text(encoding="utf-8").strip()
    return ""


def sanitize_language_code(raw: str | None) -> str | None:
    if raw is None:
        return None
    cleaned = raw.strip().lower()
    if not cleaned or len(cleaned) > 16:
        return None
    if not _LANGUAGE_CODE_RE.match(cleaned):
        return None
    return cleaned


def _format_iso_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat(timespec="seconds")


def _format_participant_section(
    user_display_name: str | None,
    user_language_code: str | None,
) -> str:
    if not user_display_name and not user_language_code:
        return ""
    lines = [
        "## Участник (профиль Telegram)",
        "source: telegram_profile",
    ]
    if user_display_name:
        lines.append(f"display_name: {user_display_name}")
        lines.append(
            "name_hint: подсказка из профиля Telegram; не обязательно копировать буквально в ответ"
        )
    if user_language_code:
        lines.append(f"language_code: {user_language_code}")
    name_rules = [
        "",
        "Правила обращения:",
        "- Имя и язык — только из профиля Telegram, не из текста сообщения пользователя.",
        "- 0–1 обращение по имени за ответ, когда уместно; не в каждом ответе.",
        "- Одна форма имени за ответ; не дублируйте и не смешивайте (не «Andrey, Андрей»).",
        "- Не сочетайте имя и приветствие неловко (не «Имя, привет»).",
    ]
    if user_language_code and user_language_code.startswith("ru"):
        name_rules.append(
            "- При language_code ru предпочитайте естественную русскую форму имени, "
            "если она очевидна (Andrey → Андрей), вместо буквальной латиницы из профиля."
        )
    elif user_display_name:
        name_rules.append(
            "- Если диалог на русском, можно использовать естественную русскую форму имени "
            "вместо латиницы из профиля, когда это уместно."
        )
    name_rules.append("- На короткие реплики вроде «привет» отвечайте кратко и естественно.")
    lines.extend(name_rules)
    return "\n".join(lines)


def _format_temporal_section(
    *,
    current_time_utc: datetime,
    last_user_message_at: datetime | None,
) -> str:
    lines = [
        "## Временной контекст",
        f"current_time_utc: {_format_iso_utc(current_time_utc)}",
    ]
    if last_user_message_at is not None:
        lines.append(f"last_user_message_at: {_format_iso_utc(last_user_message_at)}")
    else:
        lines.append(
            "last_user_message_at: нет предыдущего сообщения пользователя в этой сессии"
        )
        lines.append("session_note: первое сообщение пользователя в этой сессии")
    return "\n".join(lines)


def build_dialogue_prompt(
    *,
    user_message: str,
    session_context: str,
    recent_dialogue: str,
    user_display_name: str | None = None,
    user_language_code: str | None = None,
    current_time_utc: datetime | None = None,
    last_user_message_at: datetime | None = None,
) -> str:
    now = current_time_utc or datetime.now(timezone.utc)
    language = sanitize_language_code(user_language_code)
    style = load_companion_style_anchor()
    return "\n\n".join(
        part
        for part in (
            style,
            "## Текущий контекст сессии",
            session_context or "(нет дополнительного контекста)",
            "## Недавний диалог",
            recent_dialogue or "(первое сообщение в сессии)",
            _format_participant_section(user_display_name, language),
            _format_temporal_section(
                current_time_utc=now,
                last_user_message_at=last_user_message_at,
            ),
            "## Сообщение пользователя",
            user_message,
            _DIALOGUE_OUTPUT_INSTRUCTIONS.strip(),
        )
        if part
    )
