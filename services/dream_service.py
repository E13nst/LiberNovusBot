# stdlib
from uuid import UUID

# thirdparty
from sqlalchemy.ext.asyncio import AsyncSession

# project
from db.models.dream_model import Dream


async def create_dream(db: AsyncSession, user_id: int, text: str, session_id: UUID) -> Dream:
    dream = Dream(user_id=user_id, text=text, session_id=session_id)
    db.add(dream)
    await db.flush()
    return dream
