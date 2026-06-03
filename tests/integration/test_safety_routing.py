# thirdparty
import pytest

# project
from services.dialogue_policy import DialoguePolicyEngine, PolicyRoute
from services.dialogue_policy.router import DialoguePolicyRouter
from services.dialogue_policy.types import InputType, SessionState

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_crisis_message_routes_to_safety(db_session, user_id):
    router = DialoguePolicyRouter(session_state_resolver=lambda _db, _uid: SessionState.ACTIVE)
    decision = await router.decide(
        db=db_session,
        user_id=user_id,
        text="я хочу умереть",
    )
    assert decision.route == PolicyRoute.ROUTE_SAFETY


def test_engine_safety_precedes_other_rules():
    from services.dialogue_policy.types import PolicyInput

    decision = DialoguePolicyEngine().decide(
        PolicyInput(
            text="я хочу умереть",
            text_length=10,
            token_count=3,
            input_type=InputType.TEXT,
            session_state=SessionState.ACTIVE,
            is_empty=False,
            crisis_signal=True,
        )
    )
    assert decision.route == PolicyRoute.ROUTE_SAFETY
