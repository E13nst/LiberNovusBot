# stdlib
import logging
from uuid import UUID

# thirdparty
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# project
from db.models.dream_model import Dream
from services.memory.dream_memory_service import MEMORY_VERSION, upsert_dream_memory
from services.memory.memory_extractor import MemoryExtractor
from services.runtime.runtime_types import NonRetryableAnalysisError

logger = logging.getLogger(__name__)
_extractor = MemoryExtractor()


async def enrich_dream_memory(
    db: AsyncSession,
    *,
    session_id: UUID,
    dream_id: int,
    user_id: int,
    analysis_job_id: UUID | None = None,
) -> None:
    """Background enrichment: direct factual extraction -> dream-scoped structured memory."""
    dream = await db.scalar(select(Dream).where(Dream.id == dream_id, Dream.session_id == session_id))
    if dream is None:
        raise NonRetryableAnalysisError(f"Dream {dream_id} not found for session {session_id}")

    memory = await _extractor.extract(
        db,
        session_id=session_id,
        dream_id=dream_id,
    )
    if not memory.dream_details:
        memory = memory.model_copy(update={"dream_details": [dream.text[:500]]})

    await upsert_dream_memory(
        db,
        dream_id=dream_id,
        session_id=session_id,
        user_id=user_id,
        memory=memory,
        analysis_job_id=analysis_job_id,
    )
    logger.info(
        "Dream memory enriched",
        extra={
            "dream_id": dream_id,
            "session_id": str(session_id),
            "memory_version": MEMORY_VERSION,
            "analysis_job_id": str(analysis_job_id) if analysis_job_id else None,
        },
    )
