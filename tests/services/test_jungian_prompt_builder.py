# stdlib
import uuid
from datetime import datetime, timedelta

# thirdparty
import pytest

# project
from db.models.dream_model import Dream
from db.models.session_summary_model import SessionSummary
from services.jungian_prompt_builder import PROMPT_PREFIX, build_jungian_prompt
from services.prompt_contract import JUNGIAN_PROMPT_CONTRACT_V1
from services.prompt_validation import validate_prompt_safety, validate_prompt_structure

_SESSION_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
_USER_ID = 987654321
_CREATED_AT = datetime(2026, 5, 26, 10, 0, 0)
_LAST_ACTIVITY_AT = datetime(2026, 5, 26, 18, 30, 0)


def _make_summary(**overrides) -> SessionSummary:
    defaults = {
        "id": uuid.uuid4(),
        "session_id": _SESSION_ID,
        "user_id": _USER_ID,
        "dream_count": 2,
        "key_symbols": ["water", "forest"],
        "recurring_words": ["dark"],
        "raw_text_sample": "I was swimming in a dark forest.",
        "created_at": _CREATED_AT,
    }
    defaults.update(overrides)
    return SessionSummary(**defaults)


def _make_dream(dream_id: int, text: str, created_at: datetime) -> Dream:
    return Dream(
        id=dream_id,
        user_id=_USER_ID,
        text=text,
        created_at=created_at,
        session_id=_SESSION_ID,
    )


def _build_prompt(**kwargs):
    summary = kwargs.pop("summary", _make_summary())
    dreams = kwargs.pop(
        "dreams",
        [
            _make_dream(1, "I was swimming in a dark forest.", _CREATED_AT),
            _make_dream(2, "A wolf appeared near the water.", _CREATED_AT + timedelta(hours=1)),
        ],
    )
    return build_jungian_prompt(
        summary,
        dreams,
        last_activity_at=kwargs.pop("last_activity_at", _LAST_ACTIVITY_AT),
        session_created_at=kwargs.pop("session_created_at", _CREATED_AT),
    )


def test_prompt_has_prefix():
    prompt = _build_prompt()
    assert prompt.startswith(PROMPT_PREFIX)


def test_context_block_fields():
    prompt = _build_prompt()
    assert "session_id:" in prompt
    assert str(_SESSION_ID) in prompt
    assert "user_id:" in prompt
    assert str(_USER_ID) in prompt
    assert "dream_count:" in prompt
    assert "dream_count: 2" in prompt
    assert "last_activity_at:" in prompt
    assert "2026-05-26 18:30:00" in prompt
    assert "session_duration:" in prompt


def test_context_block_missing_activity_shows_na():
    prompt = _build_prompt(last_activity_at=None, session_created_at=None)
    assert "last_activity_at: N/A" in prompt
    assert "session_duration: N/A" in prompt


def test_dream_log_verbatim():
    dream_text = "Unique verbatim dream text — do NOT rewrite."
    prompt = _build_prompt(
        dreams=[_make_dream(1, dream_text, _CREATED_AT)],
        summary=_make_summary(dream_count=1),
    )
    assert "[DREAM 1]" in prompt
    assert f"text: {dream_text}" in prompt
    assert "timestamp: 2026-05-26 10:00:00" in prompt


def test_dream_log_sorted_by_created_at():
    later = _make_dream(2, "Second dream.", _CREATED_AT + timedelta(hours=2))
    earlier = _make_dream(1, "First dream.", _CREATED_AT)
    prompt = _build_prompt(dreams=[later, earlier])
    first_pos = prompt.index("[DREAM 1]")
    second_pos = prompt.index("[DREAM 2]")
    assert first_pos < second_pos
    assert "text: First dream." in prompt
    assert "text: Second dream." in prompt


def test_session_summary_block():
    prompt = _build_prompt()
    assert "key_symbols:" in prompt
    assert "water" in prompt
    assert "forest" in prompt
    assert "recurring_words:" in prompt
    assert "dark" in prompt
    assert "raw_text_sample:" in prompt


def test_session_summary_null_sample_shows_na():
    prompt = _build_prompt(summary=_make_summary(raw_text_sample=None))
    assert "raw_text_sample: N/A" in prompt


def test_analysis_instructions_present():
    prompt = _build_prompt()
    assert "You are a Jungian analyst." in prompt
    assert "Use ONLY provided data" in prompt
    assert "Do NOT invent facts" in prompt
    assert "insufficient data" in prompt
    assert "possible indicates" in prompt
    assert "may suggest" in prompt


def test_analytical_framework_present():
    prompt = _build_prompt()
    assert "1. Key motifs" in prompt
    assert "2. Emotional tone patterns" in prompt
    assert "3. Repeating symbols" in prompt
    assert "4. Possible archetypal themes" in prompt
    assert "5. Psychological tension / conflict" in prompt
    assert "6. Questions for further exploration" in prompt


def test_prompt_deterministic():
    summary = _make_summary()
    dreams = [_make_dream(1, "Same dream.", _CREATED_AT)]
    first = build_jungian_prompt(
        summary,
        dreams,
        last_activity_at=_LAST_ACTIVITY_AT,
        session_created_at=_CREATED_AT,
    )
    second = build_jungian_prompt(
        summary,
        dreams,
        last_activity_at=_LAST_ACTIVITY_AT,
        session_created_at=_CREATED_AT,
    )
    assert first == second


def test_validate_prompt_safety_pass():
    prompt = _build_prompt()
    assert validate_prompt_safety(prompt) is True


def test_validate_prompt_safety_fail_no_prefix():
    prompt = _build_prompt().replace(PROMPT_PREFIX, "")
    assert validate_prompt_safety(prompt) is False


def test_validate_prompt_safety_fail_forbidden_phrase():
    prompt = _build_prompt() + "\nLet me guess what happened."
    assert validate_prompt_safety(prompt) is False


def test_validate_prompt_safety_fail_missing_anchor():
    prompt = _build_prompt().replace("Use ONLY provided data", "Use whatever you know")
    assert validate_prompt_safety(prompt) is False


def test_validate_prompt_structure_pass_on_built_prompt():
    prompt = _build_prompt()
    assert validate_prompt_structure(prompt) == []


def test_validate_prompt_structure_fail_wrong_section_order():
    prompt = _build_prompt()
    swapped = prompt.replace(
        "## 1. CONTEXT BLOCK (FACTS ONLY)",
        "## 9. CONTEXT BLOCK (FACTS ONLY)",
    )
    errors = validate_prompt_structure(swapped)
    assert any(error.code == "missing_section" for error in errors)


def test_validate_prompt_structure_fail_missing_context_field():
    prompt = _build_prompt().replace("dream_count:", "missing_count:")
    errors = validate_prompt_structure(prompt)
    assert any(error.code == "missing_context_field" for error in errors)


def test_validate_prompt_structure_fail_missing_framework_item():
    prompt = _build_prompt().replace("6. Questions for further exploration", "")
    errors = validate_prompt_structure(prompt)
    assert any(error.code == "framework" for error in errors)


def test_contract_defines_required_sections():
    contract = JUNGIAN_PROMPT_CONTRACT_V1
    assert len(contract.sections) == 5
    assert contract.sections[0].fields[0].name == "session_id"
    assert contract.sections[1].dream_entry is True
