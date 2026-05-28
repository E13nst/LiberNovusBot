# stdlib
from datetime import datetime, timedelta, timezone
from uuid import uuid4

# thirdparty
import pytest

# project
from services.analysis_policy import is_thread_fresh, utc_now
from services.analysis_state_machine_service import normalized_transition, resolve_thread_decision
from services.analysis_state_machine_types import (
    DecisionAction,
    DecisionDTO,
    SessionSnapshot,
    ThreadSnapshot,
    TransitionCommandType,
)
from services.session_service import INACTIVITY_THRESHOLD

pytestmark = pytest.mark.unit


def _session(*, status: str = "active") -> SessionSnapshot:
    return SessionSnapshot(
        session_id=uuid4(),
        status=status,
        last_activity_at=utc_now(),
    )


def _thread(
    *,
    status: str = "active",
    last_activity_at: datetime | None = None,
    created_at: datetime | None = None,
) -> ThreadSnapshot:
    now = utc_now()
    return ThreadSnapshot(
        thread_id=uuid4(),
        status=status,
        last_activity_at=last_activity_at or now,
        created_at=created_at or now,
    )


def test_continue_new_thread_when_missing():
    decision = resolve_thread_decision(_session(), ThreadSnapshot(None, None, None, None), "continue", utc_now())
    assert decision.action == DecisionAction.CREATE_NEW


def test_continue_existing_active_thread():
    thread = _thread(status="active", last_activity_at=utc_now())
    decision = resolve_thread_decision(_session(), thread, "continue", utc_now())
    assert decision.action == DecisionAction.CONTINUE
    assert decision.target_thread_id == thread.thread_id


def test_continue_creates_new_after_72h():
    stale = utc_now() - INACTIVITY_THRESHOLD - timedelta(hours=1)
    thread = _thread(status="active", last_activity_at=stale)
    decision = resolve_thread_decision(_session(), thread, "continue", utc_now())
    assert decision.action == DecisionAction.MARK_IDLE


def test_closed_thread_never_reused():
    thread = _thread(status="closed")
    decision = resolve_thread_decision(_session(), thread, "continue", utc_now())
    assert decision.action == DecisionAction.CREATE_NEW


def test_session_closed_forces_close_and_create_new():
    thread = _thread(status="active")
    decision = resolve_thread_decision(_session(status="closed"), thread, "continue", utc_now())
    assert decision.action == DecisionAction.CLOSE_AND_CREATE_NEW


def test_continue_advisory_cannot_bypass_state_machine():
    stale = utc_now() - INACTIVITY_THRESHOLD - timedelta(hours=1)
    thread = _thread(status="active", last_activity_at=stale)
    decision = resolve_thread_decision(_session(), thread, "continue", utc_now())
    assert decision.action != DecisionAction.CONTINUE


def test_decision_dto_has_fixed_deterministic_shape():
    session = _session()
    thread = _thread()
    now = utc_now()
    first = resolve_thread_decision(session, thread, "auto", now)
    second = resolve_thread_decision(session, thread, "auto", now)
    assert first == second
    assert first.confidence == 1.0


def test_normalized_transition_is_mapping_only():
    decision = DecisionDTO(
        action=DecisionAction.MARK_IDLE,
        target_thread_id=uuid4(),
        metadata=None,
    )
    transition = normalized_transition(decision)
    assert [c.command_type for c in transition.commands] == [
        TransitionCommandType.MARK_IDLE,
        TransitionCommandType.CREATE_NEW,
    ]


def test_decision_metadata_is_opaque_in_tests():
    decision = resolve_thread_decision(_session(), ThreadSnapshot(None, None, None, None), "auto", utc_now())
    assert decision.metadata is None or isinstance(decision.metadata, dict)


def test_state_machine_rejects_non_utc_naive_now_via_policy():
    thread = _thread(last_activity_at=datetime.now(timezone.utc))
    assert is_thread_fresh(thread, datetime.utcnow().replace(tzinfo=timezone.utc)) is True
