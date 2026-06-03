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
    crisis_signal: bool = False,
) -> PolicyInput:
    return PolicyInput(
        text=text,
        text_length=len(text) if text_length is None else text_length,
        token_count=len(text.split()) if token_count is None else token_count,
        input_type=input_type,
        session_state=session_state,
        is_empty=not text.strip(),
        crisis_signal=crisis_signal,
    )


def test_empty_message_routes_to_noop():
    decision = DialoguePolicyEngine().decide(_input(text="   "))
    assert decision.route == PolicyRoute.ROUTE_NOOP


def test_crisis_routes_to_safety():
    decision = DialoguePolicyEngine().decide(_input(text="я хочу умереть", crisis_signal=True))
    assert decision.route == PolicyRoute.ROUTE_SAFETY


def test_short_fragment_routes_to_clarification():
    decision = DialoguePolicyEngine().decide(
        _input(text="вода", session_state=SessionState.NEW, input_type=InputType.SHORT_FRAGMENT)
    )
    assert decision.route == PolicyRoute.ROUTE_CLARIFICATION


def test_long_text_new_session_routes_to_new_dream():
    decision = DialoguePolicyEngine().decide(
        _input(
            text="Мне приснился длинный сон про дом, воду и тень, и я проснулся с сильной тревогой.",
            session_state=SessionState.NEW,
            input_type=InputType.LONG_TEXT,
            token_count=16,
        )
    )
    assert decision.route == PolicyRoute.ROUTE_NEW_DREAM


def test_continuation_signal_routes_to_dialogue_turn():
    decision = DialoguePolicyEngine().decide(
        _input(
            text="добавлю детали прошлого сна",
            session_state=SessionState.ACTIVE,
            input_type=InputType.CONTINUATION_SIGNAL,
            token_count=4,
        )
    )
    assert decision.route == PolicyRoute.ROUTE_DIALOGUE_TURN


def test_active_short_follow_up_routes_to_dialogue_turn():
    decision = DialoguePolicyEngine().decide(
        _input(
            text="отец умер два года назад",
            session_state=SessionState.ACTIVE,
            input_type=InputType.TEXT,
            token_count=5,
        )
    )
    assert decision.route == PolicyRoute.ROUTE_DIALOGUE_TURN
