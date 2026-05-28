# stdlib
from datetime import datetime
from typing import Literal

# project
from services.analysis_policy import (
    ensure_utc,
    is_session_closed,
    is_thread_closed,
    is_thread_fresh,
    is_thread_idle,
)
from services.analysis_state_machine_types import (
    DecisionAction,
    DecisionDTO,
    SessionSnapshot,
    ThreadSnapshot,
)

AnalysisModeRequest = Literal["auto", "new", "continue"]


def resolve_thread_decision(
    session_snapshot: SessionSnapshot,
    thread_snapshot: ThreadSnapshot,
    mode: AnalysisModeRequest,
    now: datetime,
) -> DecisionDTO:
    """Pure deterministic decision over immutable snapshots. No DB or ORM access."""
    now_utc = ensure_utc(now)
    target_id = thread_snapshot.thread_id

    if is_session_closed(session_snapshot):
        return DecisionDTO(
            action=DecisionAction.CLOSE_AND_CREATE_NEW,
            target_thread_id=target_id,
            metadata={"rule": "session_closed"},
        )

    if thread_snapshot.thread_id is None:
        return DecisionDTO(
            action=DecisionAction.CREATE_NEW,
            target_thread_id=None,
            metadata={"rule": "missing_thread"},
        )

    if is_thread_closed(thread_snapshot):
        return DecisionDTO(
            action=DecisionAction.CREATE_NEW,
            target_thread_id=target_id,
            metadata={"rule": "thread_closed"},
        )

    if is_thread_idle(thread_snapshot):
        return DecisionDTO(
            action=DecisionAction.CREATE_NEW,
            target_thread_id=target_id,
            metadata={"rule": "thread_idle"},
        )

    if not is_thread_fresh(thread_snapshot, now_utc):
        return DecisionDTO(
            action=DecisionAction.MARK_IDLE,
            target_thread_id=target_id,
            metadata={"rule": "stale_thread"},
        )

    if mode == "new":
        return DecisionDTO(
            action=DecisionAction.CREATE_NEW,
            target_thread_id=target_id,
            metadata={"rule": "mode_new"},
        )

    return DecisionDTO(
        action=DecisionAction.CONTINUE,
        target_thread_id=target_id,
        metadata={"rule": "continue_allowed"},
    )


from services.analysis_state_machine_types import NormalizedTransition, TransitionCommand, TransitionCommandType

_ACTION_COMMAND_MAP: dict[DecisionAction, tuple[TransitionCommandType, ...]] = {
    DecisionAction.CONTINUE: (TransitionCommandType.CONTINUE,),
    DecisionAction.CREATE_NEW: (TransitionCommandType.CREATE_NEW,),
    DecisionAction.MARK_IDLE: (
        TransitionCommandType.MARK_IDLE,
        TransitionCommandType.CREATE_NEW,
    ),
    DecisionAction.CLOSE_AND_CREATE_NEW: (
        TransitionCommandType.CLOSE_THREAD,
        TransitionCommandType.CREATE_NEW,
    ),
}


def normalized_transition(decision: DecisionDTO) -> NormalizedTransition:
    """Static action -> command template mapping only. No business branching."""
    command_types = _ACTION_COMMAND_MAP[decision.action]
    commands = tuple(
        TransitionCommand(
            command_type=command_type,
            thread_id=decision.target_thread_id
            if command_type
            in (
                TransitionCommandType.CONTINUE,
                TransitionCommandType.MARK_IDLE,
                TransitionCommandType.CLOSE_THREAD,
            )
            else None,
        )
        for command_type in command_types
    )
    return NormalizedTransition(
        action=decision.action,
        target_thread_id=decision.target_thread_id,
        commands=commands,
    )
