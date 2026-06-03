from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.dialogue_policy_trace_model import DialoguePolicyTrace
from services.dialogue_policy import PolicyDecision, PolicyInput


def policy_input_projection(policy_input: PolicyInput) -> dict[str, Any]:
    """Project PolicyInput without persisting raw message text."""
    return {
        "text_length": policy_input.text_length,
        "token_count": policy_input.token_count,
        "input_type": policy_input.input_type.value,
        "session_state": policy_input.session_state.value,
        "is_empty": policy_input.is_empty,
        "crisis_signal": policy_input.crisis_signal,
    }


def policy_decision_projection(decision: PolicyDecision) -> dict[str, Any]:
    return {
        "route": decision.route.value,
        "session_action": decision.session_action.value,
        "reason_code": decision.reason_code,
        "confidence": decision.confidence,
    }


async def record_policy_trace(
    db: AsyncSession,
    *,
    user_id: int,
    policy_input: PolicyInput,
    decision: PolicyDecision,
    outcome: dict[str, Any],
    session_id: UUID | None = None,
    dream_id: int | None = None,
    job_id: UUID | None = None,
) -> DialoguePolicyTrace:
    trace = DialoguePolicyTrace(
        user_id=user_id,
        session_id=session_id,
        dream_id=dream_id,
        job_id=job_id,
        input_json=policy_input_projection(policy_input),
        decision_json=policy_decision_projection(decision),
        route=decision.route.value,
        reason_code=decision.reason_code,
        outcome_json=outcome,
    )
    db.add(trace)
    await db.flush()
    return trace


async def list_session_policy_traces(
    db: AsyncSession,
    session_id: UUID,
) -> list[DialoguePolicyTrace]:
    result = await db.execute(
        select(DialoguePolicyTrace)
        .where(DialoguePolicyTrace.session_id == session_id)
        .order_by(DialoguePolicyTrace.created_at.asc(), DialoguePolicyTrace.id.asc())
    )
    return list(result.scalars().all())
