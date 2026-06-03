# stdlib
from uuid import UUID

# thirdparty
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# project
from db.models.dream_memory_model import DreamMemory
from services.analysis.schema.structured_dream_memory_v1 import StructuredDreamMemoryV1

MEMORY_VERSION = "structured_dream_v1"


async def upsert_dream_memory(
    db: AsyncSession,
    *,
    dream_id: int,
    session_id: UUID,
    user_id: int,
    memory: StructuredDreamMemoryV1,
    analysis_job_id: UUID | None = None,
) -> DreamMemory:
    existing = await db.scalar(select(DreamMemory).where(DreamMemory.dream_id == dream_id))
    payload = memory.model_dump()
    if existing is None:
        row = DreamMemory(
            dream_id=dream_id,
            session_id=session_id,
            user_id=user_id,
            memory_version=MEMORY_VERSION,
            memory_json=payload,
            analysis_job_id=analysis_job_id,
        )
        db.add(row)
        await db.flush()
        return row

    existing.memory_json = payload
    existing.memory_version = MEMORY_VERSION
    if analysis_job_id is not None:
        existing.analysis_job_id = analysis_job_id
    await db.flush()
    return existing


async def get_dream_memory(db: AsyncSession, dream_id: int) -> DreamMemory | None:
    return await db.scalar(select(DreamMemory).where(DreamMemory.dream_id == dream_id))
