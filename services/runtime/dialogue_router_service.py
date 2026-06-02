# stdlib
from dataclasses import dataclass
from typing import Any

# thirdparty
from sqlalchemy.ext.asyncio import AsyncSession

# project
from services.dialogue_policy import DialoguePolicyRouter, PolicyRoute, SessionAction
from services.admin.policy_trace_service import record_policy_trace
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
    if hasattr(router, "evaluate"):
        evaluation = await router.evaluate(db=db, user_id=telegram_id, text=text)
        policy_input = evaluation.policy_input
        decision = evaluation.decision
    else:
        decision = await router.decide(db=db, user_id=telegram_id, text=text)
        policy_input = None

    if decision.route == PolicyRoute.ROUTE_REFLECTION:
        intake = await intake_handler(db, telegram_id=telegram_id, text=text)
        if policy_input is not None and db is not None:
            await record_policy_trace(
                db,
                user_id=telegram_id,
                policy_input=policy_input,
                decision=decision,
                session_id=intake.dream.session_id,
                dream_id=intake.dream.id,
                job_id=intake.job.id,
                outcome={
                    "kind": "reflection_enqueued",
                    "dream_id": intake.dream.id,
                    "job_id": str(intake.job.id),
                    "session_id": str(intake.dream.session_id),
                },
            )
        return DialogueRoutingResult(
            route=decision.route,
            reason_code=decision.reason_code,
            session_action=decision.session_action,
            intake_result=intake,
        )

    if decision.route == PolicyRoute.ROUTE_CLARIFICATION:
        if policy_input is not None and db is not None:
            await record_policy_trace(
                db,
                user_id=telegram_id,
                policy_input=policy_input,
                decision=decision,
                outcome={"kind": "clarification_response"},
            )
        return DialogueRoutingResult(
            route=decision.route,
            reason_code=decision.reason_code,
            session_action=decision.session_action,
            immediate_response=build_clarification_response(),
        )

    if decision.route == PolicyRoute.ROUTE_SESSION_CONTINUE:
        if policy_input is not None and db is not None:
            await record_policy_trace(
                db,
                user_id=telegram_id,
                policy_input=policy_input,
                decision=decision,
                outcome={"kind": "session_continue_response"},
            )
        return DialogueRoutingResult(
            route=decision.route,
            reason_code=decision.reason_code,
            session_action=decision.session_action,
            immediate_response=build_session_continue_response(),
        )

    if policy_input is not None and db is not None:
        await record_policy_trace(
            db,
            user_id=telegram_id,
            policy_input=policy_input,
            decision=decision,
            outcome={"kind": "noop"},
        )
    return DialogueRoutingResult(
        route=decision.route,
        reason_code=decision.reason_code,
        session_action=decision.session_action,
    )

