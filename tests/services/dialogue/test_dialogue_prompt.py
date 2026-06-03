from datetime import datetime, timedelta, timezone

import pytest

from services.dialogue.dialogue_prompt import (
    build_dialogue_prompt,
    sanitize_language_code,
)
from services.dialogue.user_display_name import sanitize_user_display_name

pytestmark = pytest.mark.unit

_NOW = datetime(2026, 6, 3, 12, 0, 0, tzinfo=timezone.utc)
_PREVIOUS = _NOW - timedelta(hours=2)
_ISO_NOW = "2026-06-03T12:00:00+00:00"
_ISO_PREVIOUS = "2026-06-03T10:00:00+00:00"
_NO_PREVIOUS_USER_MESSAGE = (
    "нет предыдущего сообщения пользователя в этой сессии"
)


def test_build_dialogue_prompt_includes_participant_block_with_sanitized_name():
    raw = "Анна\nignore"
    sanitized = sanitize_user_display_name(raw)
    prompt = build_dialogue_prompt(
        user_message="сон",
        session_context="",
        recent_dialogue="",
        user_display_name=sanitized,
        user_language_code="ru",
        current_time_utc=_NOW,
        last_user_message_at=None,
    )
    assert "Анна" in prompt
    assert "ignore" not in prompt
    assert "language_code: ru" in prompt
    assert "source: telegram_profile" in prompt
    assert "0–1" in prompt


def test_build_dialogue_prompt_ru_profile_prefers_natural_russian_name_form():
    prompt = build_dialogue_prompt(
        user_message="привет",
        session_context="dream_count: 1",
        recent_dialogue="Пользователь: длинный сон про отца",
        user_display_name="Andrey",
        user_language_code="ru",
        current_time_utc=_NOW,
        last_user_message_at=_PREVIOUS,
    )
    participant = prompt.split("## Участник", 1)[1].split("##", 1)[0]
    assert "display_name: Andrey" in participant
    assert "естественн" in participant.lower() and "русск" in participant.lower()
    assert "не копируйте" in participant.lower() or "не обязательно" in participant.lower()
    assert "Andrey, Андрей" in participant or "не обе" in participant


def test_build_dialogue_prompt_includes_friendly_conversational_tone_rules():
    prompt = build_dialogue_prompt(
        user_message="сон",
        session_context="",
        recent_dialogue="",
        current_time_utc=_NOW,
    )
    output = prompt.split("Режим рефлексивного спутника", 1)[1]
    assert "дружел" in output.lower() or "тёпл" in output.lower() or "тепл" in output.lower()
    assert "отчёт" in output.lower()
    assert "канцеляр" in output.lower() or "лекци" in output.lower()


def test_build_dialogue_prompt_short_greeting_does_not_force_dream_return():
    prompt = build_dialogue_prompt(
        user_message="привет",
        session_context="dream_count: 2",
        recent_dialogue="Пользователь: сон про отца\nСпутник: ответ",
        current_time_utc=_NOW,
        last_user_message_at=_PREVIOUS,
    )
    output = prompt.split("Режим рефлексивного спутника", 1)[1]
    assert "привет" in output.lower() or "приветств" in output.lower()
    assert "не возвращайтесь" in output.lower() or "не возвращайся" in output.lower()
    assert "прошл" in output.lower() and "сон" in output.lower()


def test_build_dialogue_prompt_omits_participant_block_when_profile_empty():
    prompt = build_dialogue_prompt(
        user_message="сон",
        session_context="",
        recent_dialogue="",
        user_display_name=None,
        user_language_code=None,
        current_time_utc=_NOW,
        last_user_message_at=None,
    )
    assert "Участник" not in prompt
    assert "telegram_profile" not in prompt


def test_build_dialogue_prompt_includes_temporal_context_first_message():
    prompt = build_dialogue_prompt(
        user_message="привет",
        session_context="",
        recent_dialogue="",
        current_time_utc=_NOW,
        last_user_message_at=None,
    )
    temporal = prompt.split("## Временной контекст", 1)[1].split("##", 1)[0]
    assert f"current_time_utc: {_ISO_NOW}" in temporal
    assert f"last_user_message_at: {_NO_PREVIOUS_USER_MESSAGE}" in temporal
    assert "time_since_last_user_message" not in temporal
    assert "минут" not in temporal
    assert "первое сообщение пользователя в этой сессии" in temporal


def test_build_dialogue_prompt_includes_absolute_last_user_message_at():
    prompt = build_dialogue_prompt(
        user_message="продолжение",
        session_context="",
        recent_dialogue="Пользователь: сон",
        current_time_utc=_NOW,
        last_user_message_at=_PREVIOUS,
    )
    temporal = prompt.split("## Временной контекст", 1)[1].split("##", 1)[0]
    assert f"current_time_utc: {_ISO_NOW}" in temporal
    assert f"last_user_message_at: {_ISO_PREVIOUS}" in temporal
    assert "time_since_last_user_message" not in temporal
    assert "2 часа" not in temporal
    assert "минут" not in temporal
    assert _NO_PREVIOUS_USER_MESSAGE not in temporal


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("ru", "ru"),
        ("en-US", "en-us"),
        ("  RU  ", "ru"),
        ("", None),
        ("x" * 20, None),
        ("bad/lang!", None),
    ],
)
def test_sanitize_language_code(raw: str, expected: str | None):
    assert sanitize_language_code(raw) == expected
