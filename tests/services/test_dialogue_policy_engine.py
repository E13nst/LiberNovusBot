# thirdparty
import pytest

# project
from services.dialogue_policy import (
    DialoguePolicyEngine,
    InputType,
    PolicyInput,
    PolicyRoute,
    SessionState,
)

pytestmark = pytest.mark.unit


def _input(
    *,
    text: str,
    session_state: SessionState = SessionState.NEW,
    input_type: InputType = InputType.TEXT,
    text_length: int | None = None,
    token_count: int | None = None,
) -> PolicyInput:
    return PolicyInput(
        text=text,
        text_length=len(text) if text_length is None else text_length,
        token_count=len(text.split()) if token_count is None else token_count,
        input_type=input_type,
        session_state=session_state,
        is_empty=not text.strip(),
    )


def test_empty_message_routes_to_noop():
    decision = DialoguePolicyEngine().decide(_input(text="   "))
    assert decision.route == PolicyRoute.ROUTE_NOOP
    assert decision.confidence == 1.0


def test_short_fragment_without_active_context_routes_to_clarification():
    decision = DialoguePolicyEngine().decide(
        _input(text="вода", session_state=SessionState.NEW, input_type=InputType.SHORT_FRAGMENT)
    )
    assert decision.route == PolicyRoute.ROUTE_CLARIFICATION


def test_long_text_with_new_session_routes_to_reflection():
    decision = DialoguePolicyEngine().decide(
        _input(
            text="Мне приснился длинный сон про дом, воду и тень, и я проснулся с сильной тревогой.",
            session_state=SessionState.NEW,
            input_type=InputType.LONG_TEXT,
            token_count=16,
        )
    )
    assert decision.route == PolicyRoute.ROUTE_REFLECTION


def test_active_session_with_continuation_signal_routes_to_continue():
    decision = DialoguePolicyEngine().decide(
        _input(
            text="добавлю детали прошлого сна",
            session_state=SessionState.ACTIVE,
            input_type=InputType.CONTINUATION_SIGNAL,
            token_count=4,
        )
    )
    assert decision.route == PolicyRoute.ROUTE_SESSION_CONTINUE


def test_active_session_with_sufficient_tokens_routes_to_reflection():
    decision = DialoguePolicyEngine().decide(
        _input(
            text="В продолжение: я шел по длинному коридору, потом увидел дверь и не смог открыть ее.",
            session_state=SessionState.ACTIVE,
            input_type=InputType.LONG_TEXT,
            token_count=18,
        )
    )
    assert decision.route == PolicyRoute.ROUTE_REFLECTION


def test_closed_session_never_routes_to_continue_without_signal():
    decision = DialoguePolicyEngine().decide(
        _input(
            text="короткий фрагмент",
            session_state=SessionState.CLOSED,
            input_type=InputType.SHORT_FRAGMENT,
            token_count=2,
        )
    )
    assert decision.route != PolicyRoute.ROUTE_SESSION_CONTINUE


def test_decision_is_deterministic_for_same_input():
    sample = _input(
        text="повторяющийся ввод",
        session_state=SessionState.IDLE,
        input_type=InputType.TEXT,
        token_count=2,
    )
    engine = DialoguePolicyEngine()
    first = engine.decide(sample)
    second = engine.decide(sample)
    assert first == second
    assert first.confidence == 1.0
