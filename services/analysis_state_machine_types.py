# stdlib
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID


class DecisionAction(str, Enum):
    CONTINUE = "CONTINUE"
    CREATE_NEW = "CREATE_NEW"
    MARK_IDLE = "MARK_IDLE"
    CLOSE_AND_CREATE_NEW = "CLOSE_AND_CREATE_NEW"


class TransitionCommandType(str, Enum):
    CONTINUE = "CONTINUE"
    CREATE_NEW = "CREATE_NEW"
    MARK_IDLE = "MARK_IDLE"
    CLOSE_THREAD = "CLOSE_THREAD"


@dataclass(frozen=True)
class SessionSnapshot:
    session_id: UUID
    status: str
    last_activity_at: datetime | None


@dataclass(frozen=True)
class ThreadSnapshot:
    thread_id: UUID | None
    status: str | None
    last_activity_at: datetime | None
    created_at: datetime | None


@dataclass(frozen=True)
class DecisionDTO:
    action: DecisionAction
    target_thread_id: UUID | None
    metadata: dict[str, Any] | None
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if self.confidence != 1.0:
            raise ValueError("DecisionDTO.confidence must be 1.0 for deterministic state machine")


@dataclass(frozen=True)
class TransitionCommand:
    command_type: TransitionCommandType
    thread_id: UUID | None = None


@dataclass(frozen=True)
class NormalizedTransition:
    action: DecisionAction
    target_thread_id: UUID | None
    commands: tuple[TransitionCommand, ...]


@dataclass(frozen=True)
class ResolvedThreadResult:
    thread_id: UUID
    mode_resolved: str


class StateMachineConcurrencyError(Exception):
    """Raised when bounded re-resolve is exhausted after a concurrent state change."""
