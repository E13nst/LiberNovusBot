from dataclasses import dataclass

import pytest

from services.dialogue_policy import PolicyDecision, PolicyRoute, SessionAction
from services.runtime.dialogue_router_service import process_incoming_message

pytestmark = pytest.mark.unit


@dataclass(frozen=True)
class _FakeIntakeResult:
    dream_id: int
    job_id: int


class _StubPolicyRouter:
    def __init__(self, decision: PolicyDecision):
        self._decision = decision
        self.calls = 0

    async def decide(self, *, db, user_id: int, text: str) -> PolicyDecision:  # noqa: ARG002
        self.calls += 1
        return self._decision


@pytest.mark.asyncio
async def test_reflection_route_calls_intake_once():
    decision = PolicyDecision(
        route=PolicyRoute.ROUTE_REFLECTION,
        session_action=SessionAction.START_NEW,
        reason_code="test_reflection",
    )
    router = _StubPolicyRouter(decision)
    calls = {"count": 0}

    async def _intake(db, telegram_id: int, text: str):  # noqa: ARG001
        calls["count"] += 1
        return _FakeIntakeResult(dream_id=1, job_id=2)

    result = await process_incoming_message(
        db=None,
        telegram_id=123,
        text="Мне приснился длинный сон про дом и тень у воды.",
        policy_router=router,
        intake_handler=_intake,
    )

    assert router.calls == 1
    assert calls["count"] == 1
    assert result.route == PolicyRoute.ROUTE_REFLECTION
    assert result.intake_result is not None
    assert result.immediate_response is None


@pytest.mark.asyncio
async def test_clarification_route_returns_immediate_response_without_intake():
    decision = PolicyDecision(
        route=PolicyRoute.ROUTE_CLARIFICATION,
        reason_code="test_clarification",
    )
    router = _StubPolicyRouter(decision)
    calls = {"count": 0}

    async def _intake(db, telegram_id: int, text: str):  # noqa: ARG001
        calls["count"] += 1
        return _FakeIntakeResult(dream_id=1, job_id=2)

    result = await process_incoming_message(
        db=None,
        telegram_id=123,
        text="вода",
        policy_router=router,
        intake_handler=_intake,
    )

    assert router.calls == 1
    assert calls["count"] == 0
    assert result.route == PolicyRoute.ROUTE_CLARIFICATION
    assert result.immediate_response is not None
    assert result.intake_result is None


@pytest.mark.asyncio
async def test_session_continue_route_returns_immediate_response_without_intake():
    decision = PolicyDecision(
        route=PolicyRoute.ROUTE_SESSION_CONTINUE,
        session_action=SessionAction.CONTINUE,
        reason_code="test_continue",
    )
    router = _StubPolicyRouter(decision)
    calls = {"count": 0}

    async def _intake(db, telegram_id: int, text: str):  # noqa: ARG001
        calls["count"] += 1
        return _FakeIntakeResult(dream_id=1, job_id=2)

    result = await process_incoming_message(
        db=None,
        telegram_id=123,
        text="добавлю детали прошлого сна",
        policy_router=router,
        intake_handler=_intake,
    )

    assert router.calls == 1
    assert calls["count"] == 0
    assert result.route == PolicyRoute.ROUTE_SESSION_CONTINUE
    assert result.immediate_response is not None
    assert result.intake_result is None


@pytest.mark.asyncio
async def test_noop_route_skips_intake_and_has_no_immediate_response():
    decision = PolicyDecision(
        route=PolicyRoute.ROUTE_NOOP,
        reason_code="test_noop",
    )
    router = _StubPolicyRouter(decision)
    calls = {"count": 0}

    async def _intake(db, telegram_id: int, text: str):  # noqa: ARG001
        calls["count"] += 1
        return _FakeIntakeResult(dream_id=1, job_id=2)

    result = await process_incoming_message(
        db=None,
        telegram_id=123,
        text="   ",
        policy_router=router,
        intake_handler=_intake,
    )

    assert router.calls == 1
    assert calls["count"] == 0
    assert result.route == PolicyRoute.ROUTE_NOOP
    assert result.immediate_response is None
    assert result.intake_result is None

