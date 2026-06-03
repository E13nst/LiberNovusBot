# stdlib
from uuid import UUID

# thirdparty
from sqlalchemy.ext.asyncio import AsyncSession

# project
import settings
from db.models.conversation_turn_model import TURN_TYPE_CLARIFICATION, TURN_TYPE_DIALOGUE, TURN_TYPE_DREAM_INTAKE, TURN_TYPE_SAFETY
from services.admin.policy_trace_service import record_policy_trace
from services.conversation.conversation_turn_service import append_assistant_turn, append_user_turn
from services.dialogue.dialogue_orchestrator import generate_dialogue_turn
from services.dialogue_policy import DialoguePolicyRouter, PolicyRoute, SessionAction
from services.dream_intake import register_incoming_dream
from services.ingress.types import IngressResult
from services.prompts.jungian.clarification_prompt_ru import build_clarification_response
from services.prompts.jungian.safety_prompt_ru import build_safety_response
from services.session_service import get_or_create_active_session, update_session_activity

SAFETY_TURN_TYPE = TURN_TYPE_SAFETY


async def process_incoming_message(
    db: AsyncSession,
    *,
    telegram_id: int,
    text: str,
    user_display_name: str | None = None,
    user_language_code: str | None = None,
    policy_router: DialoguePolicyRouter | None = None,
) -> IngressResult:
    """Canonical ingress: policy once, persist turns, dialogue reply, optional memory job."""
    router = policy_router or DialoguePolicyRouter()
    evaluation = await router.evaluate(db=db, user_id=telegram_id, text=text)
    decision = evaluation.decision
    policy_input = evaluation.policy_input

    if decision.route == PolicyRoute.ROUTE_NOOP:
        await _trace(db, telegram_id, policy_input, decision, outcome={"kind": "noop"})
        return IngressResult(
            route=decision.route,
            reason_code=decision.reason_code,
            session_action=decision.session_action,
        )

    if decision.route == PolicyRoute.ROUTE_SAFETY:
        session = await get_or_create_active_session(db, user_id=telegram_id)
        outbound = build_safety_response()
        await append_user_turn(
            db,
            user_id=telegram_id,
            session_id=session.id,
            text=text,
            turn_type=SAFETY_TURN_TYPE,
        )
        await append_assistant_turn(
            db,
            user_id=telegram_id,
            session_id=session.id,
            text=outbound,
            turn_type=SAFETY_TURN_TYPE,
        )
        await update_session_activity(db, session.id)
        await _trace(db, telegram_id, policy_input, decision, session_id=session.id, outcome={"kind": "safety"})
        return IngressResult(
            route=decision.route,
            reason_code=decision.reason_code,
            session_action=decision.session_action,
            session_id=session.id,
            outbound_messages=(outbound,),
        )

    if decision.route == PolicyRoute.ROUTE_CLARIFICATION:
        session = await get_or_create_active_session(db, user_id=telegram_id)
        outbound = build_clarification_response()
        await append_user_turn(
            db,
            user_id=telegram_id,
            session_id=session.id,
            text=text,
            turn_type=TURN_TYPE_CLARIFICATION,
        )
        await append_assistant_turn(
            db,
            user_id=telegram_id,
            session_id=session.id,
            text=outbound,
            turn_type=TURN_TYPE_CLARIFICATION,
        )
        await update_session_activity(db, session.id)
        await _trace(db, telegram_id, policy_input, decision, session_id=session.id, outcome={"kind": "clarification"})
        return IngressResult(
            route=decision.route,
            reason_code=decision.reason_code,
            session_action=decision.session_action,
            session_id=session.id,
            outbound_messages=(outbound,),
        )

    session = await get_or_create_active_session(db, user_id=telegram_id)
    dream_id: int | None = None
    job_id: UUID | None = None

    if decision.route == PolicyRoute.ROUTE_NEW_DREAM:
        intake = await register_incoming_dream(db, telegram_id=telegram_id, text=text)
        dream_id = intake.dream.id
        job_id = intake.job.id
        turn_type = TURN_TYPE_DREAM_INTAKE
        await append_user_turn(
            db,
            user_id=telegram_id,
            session_id=session.id,
            text=text,
            turn_type=turn_type,
            dream_id=dream_id,
        )
        await _trace(
            db,
            telegram_id,
            policy_input,
            decision,
            session_id=session.id,
            dream_id=dream_id,
            job_id=job_id,
            outcome={"kind": "new_dream_enqueued", "dream_id": dream_id, "job_id": str(job_id)},
        )
    else:
        turn_type = TURN_TYPE_DIALOGUE
        await append_user_turn(
            db,
            user_id=telegram_id,
            session_id=session.id,
            text=text,
            turn_type=turn_type,
        )
        await update_session_activity(db, session.id)
        await _trace(
            db,
            telegram_id,
            policy_input,
            decision,
            session_id=session.id,
            outcome={"kind": "dialogue_turn"},
        )

    dialogue = await generate_dialogue_turn(
        db,
        session_id=session.id,
        user_message=text,
        user_display_name=user_display_name,
        user_language_code=user_language_code,
    )
    metadata = dialogue.model_dump()
    assistant_text = metadata.pop("assistant_message")
    await append_assistant_turn(
        db,
        user_id=telegram_id,
        session_id=session.id,
        text=assistant_text,
        turn_type=turn_type,
        dream_id=dream_id,
        metadata_json=metadata,
    )

    return IngressResult(
        route=decision.route,
        reason_code=decision.reason_code,
        session_action=decision.session_action,
        session_id=session.id,
        dream_id=dream_id,
        job_id=job_id,
        outbound_messages=(assistant_text,),
    )


async def _trace(
    db: AsyncSession,
    user_id: int,
    policy_input,
    decision,
    *,
    session_id: UUID | None = None,
    dream_id: int | None = None,
    job_id: UUID | None = None,
    outcome: dict | None = None,
) -> None:
    await record_policy_trace(
        db,
        user_id=user_id,
        policy_input=policy_input,
        decision=decision,
        session_id=session_id,
        dream_id=dream_id,
        job_id=job_id,
        outcome=outcome or {},
    )
