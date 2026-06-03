# stdlib
from dataclasses import dataclass
from enum import Enum


class InputType(str, Enum):
    TEXT = "TEXT"
    SHORT_FRAGMENT = "SHORT_FRAGMENT"
    LONG_TEXT = "LONG_TEXT"
    CONTINUATION_SIGNAL = "CONTINUATION_SIGNAL"


class SessionState(str, Enum):
    NEW = "NEW"
    ACTIVE = "ACTIVE"
    IDLE = "IDLE"
    CLOSED = "CLOSED"
    RESUMED = "RESUMED"


class PolicyRoute(str, Enum):
    ROUTE_NEW_DREAM = "ROUTE_NEW_DREAM"
    ROUTE_DIALOGUE_TURN = "ROUTE_DIALOGUE_TURN"
    ROUTE_CLARIFICATION = "ROUTE_CLARIFICATION"
    ROUTE_SAFETY = "ROUTE_SAFETY"
    ROUTE_NOOP = "ROUTE_NOOP"


class SessionAction(str, Enum):
    NONE = "NONE"
    START_NEW = "START_NEW"
    CONTINUE = "CONTINUE"


@dataclass(frozen=True)
class PolicyInput:
    text: str
    text_length: int
    token_count: int
    input_type: InputType
    session_state: SessionState
    is_empty: bool
    crisis_signal: bool = False


@dataclass(frozen=True)
class PolicyDecision:
    route: PolicyRoute
    session_action: SessionAction = SessionAction.NONE
    reason_code: str = "default"
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if self.confidence != 1.0:
            raise ValueError("PolicyDecision.confidence must be 1.0 for deterministic routing")
