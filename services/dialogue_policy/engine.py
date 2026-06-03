# project
from services.dialogue_policy.types import (
    InputType,
    PolicyDecision,
    PolicyInput,
    PolicyRoute,
    SessionAction,
    SessionState,
)

MIN_TOKENS_FOR_DREAM = 8


class DialoguePolicyEngine:
    """Pure deterministic router over structural and session-state signals."""

    def decide(self, policy_input: PolicyInput) -> PolicyDecision:
        if policy_input.crisis_signal:
            return PolicyDecision(route=PolicyRoute.ROUTE_SAFETY, reason_code="crisis_signal_detected")

        if policy_input.is_empty or policy_input.text_length <= 0:
            return PolicyDecision(route=PolicyRoute.ROUTE_NOOP, reason_code="empty_input")

        if (
            policy_input.session_state in {SessionState.NEW, SessionState.IDLE, SessionState.CLOSED}
            and policy_input.input_type == InputType.SHORT_FRAGMENT
            and policy_input.token_count < MIN_TOKENS_FOR_DREAM
        ):
            return PolicyDecision(
                route=PolicyRoute.ROUTE_CLARIFICATION,
                reason_code="short_fragment_without_context",
            )

        if policy_input.input_type == InputType.CONTINUATION_SIGNAL:
            return PolicyDecision(
                route=PolicyRoute.ROUTE_DIALOGUE_TURN,
                session_action=SessionAction.CONTINUE,
                reason_code="continuation_signal",
            )

        if (
            policy_input.session_state in {SessionState.NEW, SessionState.CLOSED}
            and policy_input.input_type == InputType.LONG_TEXT
            and policy_input.token_count >= MIN_TOKENS_FOR_DREAM
        ):
            return PolicyDecision(
                route=PolicyRoute.ROUTE_NEW_DREAM,
                session_action=SessionAction.START_NEW,
                reason_code="long_text_new_or_closed_session",
            )

        if (
            policy_input.session_state in {SessionState.ACTIVE, SessionState.RESUMED}
            and policy_input.token_count >= MIN_TOKENS_FOR_DREAM
            and policy_input.input_type == InputType.LONG_TEXT
        ):
            return PolicyDecision(
                route=PolicyRoute.ROUTE_NEW_DREAM,
                session_action=SessionAction.CONTINUE,
                reason_code="active_session_new_dream_fragment",
            )

        if policy_input.session_state in {SessionState.ACTIVE, SessionState.RESUMED}:
            if policy_input.token_count < MIN_TOKENS_FOR_DREAM:
                return PolicyDecision(
                    route=PolicyRoute.ROUTE_DIALOGUE_TURN,
                    session_action=SessionAction.CONTINUE,
                    reason_code="active_session_short_follow_up",
                )
            return PolicyDecision(
                route=PolicyRoute.ROUTE_DIALOGUE_TURN,
                session_action=SessionAction.CONTINUE,
                reason_code="active_session_dialogue_turn",
            )

        if policy_input.token_count < MIN_TOKENS_FOR_DREAM:
            return PolicyDecision(
                route=PolicyRoute.ROUTE_CLARIFICATION,
                reason_code="insufficient_tokens",
            )

        return PolicyDecision(
            route=PolicyRoute.ROUTE_NEW_DREAM,
            session_action=SessionAction.START_NEW,
            reason_code="default_new_dream_route",
        )
