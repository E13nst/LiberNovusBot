# thirdparty
from sqlalchemy.ext.asyncio import AsyncSession

# project
from db.models.dream_model import DreamModel


async def create_dream(session: AsyncSession, user_id: int, text: str) -> DreamModel:
    dream = DreamModel(user_id=user_id, text=text)
    session.add(dream)
    await session.flush()
    return dream
