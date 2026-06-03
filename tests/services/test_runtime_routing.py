# stdlib
from unittest.mock import AsyncMock, MagicMock

# thirdparty
import pytest

# project
from services.dialogue_policy import PolicyDecision, PolicyRoute, SessionAction
from services.ingress.ingress_service import process_incoming_message

pytestmark = pytest.mark.unit


class _FakeRouter:
    def __init__(self, decision: PolicyDecision):
        self.calls = 0
        self._decision = decision

    async def evaluate(self, *, db, user_id: int, text: str):
        self.calls += 1
        from services.dialogue_policy.router import PolicyEvaluation
        from services.dialogue_policy.types import InputType, PolicyInput, SessionState

        policy_input = PolicyInput(
            text=text,
            text_length=len(text),
            token_count=len(text.split()),
            input_type=InputType.TEXT,
            session_state=SessionState.ACTIVE,
            is_empty=False,
        )
        return PolicyEvaluation(policy_input=policy_input, decision=self._decision)


@pytest.mark.asyncio
async def test_new_dream_route_calls_intake(monkeypatch):
    decision = PolicyDecision(
        route=PolicyRoute.ROUTE_NEW_DREAM,
        session_action=SessionAction.START_NEW,
        reason_code="test_new_dream",
    )
    router = _FakeRouter(decision)
    calls = {"count": 0}

    async def fake_intake(db, *, telegram_id: int, text: str):
        calls["count"] += 1
        dream = MagicMock()
        dream.id = 1
        dream.session_id = "00000000-0000-0000-0000-000000000001"
        job = MagicMock()
        job.id = "00000000-0000-0000-0000-000000000002"
        result = MagicMock()
        result.dream = dream
        result.job = job
        return result

    monkeypatch.setattr("services.ingress.ingress_service.register_incoming_dream", fake_intake)
    monkeypatch.setattr(
        "services.ingress.ingress_service.get_or_create_active_session",
        AsyncMock(return_value=MagicMock(id="00000000-0000-0000-0000-000000000099")),
    )
    monkeypatch.setattr(
        "services.ingress.ingress_service.generate_dialogue_turn",
        AsyncMock(return_value=MagicMock(model_dump=lambda: {"assistant_message": "Живой ответ", "focus": [], "questions": [], "background_notes": {}, "emotional_intensity": 0.5, "safety_flags": []})),
    )
    monkeypatch.setattr("services.ingress.ingress_service.append_user_turn", AsyncMock())
    monkeypatch.setattr("services.ingress.ingress_service.append_assistant_turn", AsyncMock())
    monkeypatch.setattr("services.ingress.ingress_service._trace", AsyncMock())

    result = await process_incoming_message(MagicMock(), telegram_id=1, text="длинный сон " * 10, policy_router=router)

    assert router.calls == 1
    assert calls["count"] == 1
    assert result.route == PolicyRoute.ROUTE_NEW_DREAM
    assert result.outbound_messages == ("Живой ответ",)


@pytest.mark.asyncio
async def test_clarification_route_returns_message(monkeypatch):
    decision = PolicyDecision(route=PolicyRoute.ROUTE_CLARIFICATION, reason_code="test")
    router = _FakeRouter(decision)
    monkeypatch.setattr("services.ingress.ingress_service.get_or_create_active_session", AsyncMock(return_value=MagicMock(id="00000000-0000-0000-0000-000000000099")))
    monkeypatch.setattr("services.ingress.ingress_service.append_user_turn", AsyncMock())
    monkeypatch.setattr("services.ingress.ingress_service.append_assistant_turn", AsyncMock())
    monkeypatch.setattr("services.ingress.ingress_service.update_session_activity", AsyncMock())
    monkeypatch.setattr("services.ingress.ingress_service._trace", AsyncMock())

    result = await process_incoming_message(MagicMock(), telegram_id=1, text="вода", policy_router=router)

    assert result.route == PolicyRoute.ROUTE_CLARIFICATION
    assert len(result.outbound_messages) == 1
