# stdlib
from uuid import UUID

# thirdparty
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# project
from db.models.dream_model import Dream
from db.models.session_model import DreamSession
from services.jungian_prompt_builder import build_jungian_prompt
from services.prompt_validation import validate_prompt_safety
from services.session_summary_service import get_session_summary


async def _load_dreams(db: AsyncSession, session_id: UUID) -> list[Dream]:
    result = await db.execute(
        select(Dream)
        .where(Dream.session_id == session_id)
        .order_by(Dream.created_at.asc(), Dream.id.asc())
    )
    return list(result.scalars().all())


async def _load_session(db: AsyncSession, session_id: UUID) -> DreamSession | None:
    return await db.scalar(select(DreamSession).where(DreamSession.id == session_id))


async def generate_analysis_prompt(db: AsyncSession, session_id: UUID) -> str:
    """Load session data and return a validated Jungian analysis prompt."""
    summary = await get_session_summary(db, session_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Session summary not found")

    dreams = await _load_dreams(db, session_id)
    session = await _load_session(db, session_id)

    prompt = build_jungian_prompt(
        summary,
        dreams,
        last_activity_at=session.last_activity_at if session is not None else None,
        session_created_at=session.created_at if session is not None else None,
    )

    if not validate_prompt_safety(prompt):
        raise ValueError("Prompt failed safety validation")

    return prompt
