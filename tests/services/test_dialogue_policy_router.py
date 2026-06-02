import pytest

from services.dialogue_policy import InputType, PolicyRoute, SessionState
from services.dialogue_policy.router import DialoguePolicyRouter

pytestmark = pytest.mark.unit


def test_short_text_classified_as_short_fragment():
    router = DialoguePolicyRouter()
    assert router.classify_input_type("вода") == InputType.SHORT_FRAGMENT


def test_continuation_signal_classified_explicitly():
    router = DialoguePolicyRouter()
    assert (
        router.classify_input_type("добавлю детали прошлого сна")
        == InputType.CONTINUATION_SIGNAL
    )


@pytest.mark.asyncio
async def test_new_user_routes_short_fragment_to_clarification():
    router = DialoguePolicyRouter(session_state_resolver=lambda _db, _user_id: SessionState.NEW)
    decision = await router.decide(db=None, user_id=42, text="вода")
    assert decision.route == PolicyRoute.ROUTE_CLARIFICATION

