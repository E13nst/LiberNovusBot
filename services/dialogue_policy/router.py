# stdlib
from collections.abc import Awaitable, Callable
from inspect import isawaitable

# thirdparty
from sqlalchemy.ext.asyncio import AsyncSession

# project
from services.dialogue_policy.engine import DialoguePolicyEngine
from services.dialogue_policy.types import InputType, PolicyDecision, PolicyInput, SessionState
from services.session_service import get_active_session_raw

SessionStateResolver = Callable[[AsyncSession, int], SessionState | Awaitable[SessionState]]

_CONTINUATION_PREFIXES: tuple[str, ...] = (
    "в продолжение",
    "добавлю",
    "дополню",
    "дополнил",
    "продолжу",
    "продолжение",
    "ещё",
    "еще",
    "и ещё",
    "и еще",
)


async def _default_session_state_resolver(db: AsyncSession, user_id: int) -> SessionState:
    active = await get_active_session_raw(db, user_id)
    if active is None:
        return SessionState.NEW
    return SessionState.ACTIVE


class DialoguePolicyRouter:
    """Ingress adapter that deterministically converts inbound data into PolicyInput."""

    def __init__(
        self,
        *,
        engine: DialoguePolicyEngine | None = None,
        session_state_resolver: SessionStateResolver | None = None,
    ) -> None:
        self._engine = engine or DialoguePolicyEngine()
        self._resolve_session_state = session_state_resolver or _default_session_state_resolver

    def classify_input_type(self, text: str) -> InputType:
        normalized = " ".join(text.strip().lower().split())
        token_count = len(normalized.split()) if normalized else 0

        if any(normalized.startswith(prefix) for prefix in _CONTINUATION_PREFIXES):
            return InputType.CONTINUATION_SIGNAL
        if token_count <= 3:
            return InputType.SHORT_FRAGMENT
        if token_count >= 6 or len(normalized) >= 40:
            return InputType.LONG_TEXT
        return InputType.TEXT

    def build_policy_input(self, text: str, *, session_state: SessionState) -> PolicyInput:
        normalized = " ".join(text.split())
        token_count = len(normalized.split()) if normalized else 0
        return PolicyInput(
            text=text,
            text_length=len(normalized),
            token_count=token_count,
            input_type=self.classify_input_type(text),
            session_state=session_state,
            is_empty=not normalized,
        )

    async def decide(self, *, db: AsyncSession, user_id: int, text: str) -> PolicyDecision:
        session_state = self._resolve_session_state(db, user_id)
        if isawaitable(session_state):
            session_state = await session_state
        policy_input = self.build_policy_input(text, session_state=session_state)
        return self._engine.decide(policy_input)

