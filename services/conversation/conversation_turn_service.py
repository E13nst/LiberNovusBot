# stdlib
from datetime import datetime
from typing import Any
from uuid import UUID

# thirdparty
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# project
from db.models.conversation_turn_model import (
    TURN_ROLE_ASSISTANT,
    TURN_ROLE_USER,
    ConversationTurn,
)


async def append_turn(
    db: AsyncSession,
    *,
    user_id: int,
    session_id: UUID,
    role: str,
    turn_type: str,
    text: str,
    dream_id: int | None = None,
    source: str = "telegram",
    metadata_json: dict[str, Any] | None = None,
) -> ConversationTurn:
    turn = ConversationTurn(
        user_id=user_id,
        session_id=session_id,
        dream_id=dream_id,
        role=role,
        turn_type=turn_type,
        source=source,
        text=text,
        metadata_json=metadata_json,
    )
    db.add(turn)
    await db.flush()
    return turn


async def append_user_turn(
    db: AsyncSession,
    *,
    user_id: int,
    session_id: UUID,
    text: str,
    turn_type: str,
    dream_id: int | None = None,
) -> ConversationTurn:
    return await append_turn(
        db,
        user_id=user_id,
        session_id=session_id,
        role=TURN_ROLE_USER,
        turn_type=turn_type,
        text=text,
        dream_id=dream_id,
    )


async def append_assistant_turn(
    db: AsyncSession,
    *,
    user_id: int,
    session_id: UUID,
    text: str,
    turn_type: str,
    dream_id: int | None = None,
    metadata_json: dict[str, Any] | None = None,
) -> ConversationTurn:
    return await append_turn(
        db,
        user_id=user_id,
        session_id=session_id,
        role=TURN_ROLE_ASSISTANT,
        turn_type=turn_type,
        text=text,
        dream_id=dream_id,
        metadata_json=metadata_json,
    )


async def get_previous_user_message_at(
    db: AsyncSession,
    session_id: UUID,
) -> datetime | None:
    """Return created_at of the user turn before the most recent user turn in the session."""
    result = await db.execute(
        select(ConversationTurn.created_at)
        .where(
            ConversationTurn.session_id == session_id,
            ConversationTurn.role == TURN_ROLE_USER,
        )
        .order_by(ConversationTurn.created_at.desc(), ConversationTurn.id.desc())
        .limit(2)
    )
    rows = list(result.scalars().all())
    if len(rows) < 2:
        return None
    return rows[1]


async def list_recent_turns(
    db: AsyncSession,
    session_id: UUID,
    *,
    limit: int = 12,
) -> list[ConversationTurn]:
    result = await db.execute(
        select(ConversationTurn)
        .where(ConversationTurn.session_id == session_id)
        .order_by(ConversationTurn.created_at.desc(), ConversationTurn.id.desc())
        .limit(limit)
    )
    rows = list(result.scalars().all())
    rows.reverse()
    return rows
