# stdlib
from dataclasses import dataclass, field
from uuid import UUID

from services.dialogue_policy.types import PolicyRoute, SessionAction


@dataclass(frozen=True)
class IngressResult:
    route: PolicyRoute
    reason_code: str
    session_action: SessionAction
    session_id: UUID | None = None
    dream_id: int | None = None
    job_id: UUID | None = None
    outbound_messages: tuple[str, ...] = field(default_factory=tuple)
