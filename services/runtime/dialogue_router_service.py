# stdlib
from dataclasses import dataclass
from typing import Any

# thirdparty
from sqlalchemy.ext.asyncio import AsyncSession

# project
from services.dialogue_policy import DialoguePolicyRouter, PolicyRoute, SessionAction
from services.dream_intake import register_incoming_dream
from services.prompts.jungian.clarification_prompt_ru import (
    build_clarification_response,
    build_session_continue_response,
)


@dataclass(frozen=True)
class DialogueRoutingResult:
    route: PolicyRoute
    reason_code: str
    session_action: SessionAction
    immediate_response: str | None = None
    intake_result: Any | None = None


async def process_incoming_message(
    db: AsyncSession,
    *,
    telegram_id: int,
    text: str,
    policy_router: DialoguePolicyRouter | None = None,
    intake_handler=register_incoming_dream,
) -> DialogueRoutingResult:
    """Single decision boundary for ingress: call Policy once and execute route."""
    router = policy_router or DialoguePolicyRouter()
    decision = await router.decide(db=db, user_id=telegram_id, text=text)

    if decision.route == PolicyRoute.ROUTE_REFLECTION:
        intake = await intake_handler(db, telegram_id=telegram_id, text=text)
        return DialogueRoutingResult(
            route=decision.route,
            reason_code=decision.reason_code,
            session_action=decision.session_action,
            intake_result=intake,
        )

    if decision.route == PolicyRoute.ROUTE_CLARIFICATION:
        return DialogueRoutingResult(
            route=decision.route,
            reason_code=decision.reason_code,
            session_action=decision.session_action,
            immediate_response=build_clarification_response(),
        )

    if decision.route == PolicyRoute.ROUTE_SESSION_CONTINUE:
        return DialogueRoutingResult(
            route=decision.route,
            reason_code=decision.reason_code,
            session_action=decision.session_action,
            immediate_response=build_session_continue_response(),
        )

    return DialogueRoutingResult(
        route=decision.route,
        reason_code=decision.reason_code,
        session_action=decision.session_action,
    )

