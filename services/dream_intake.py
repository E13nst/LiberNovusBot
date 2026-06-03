# stdlib
from dataclasses import dataclass

# thirdparty
from sqlalchemy.ext.asyncio import AsyncSession

# project
import settings
from db.models.analysis_job_model import AnalysisJob
from db.models.dream_model import Dream
from services.dream_service import create_dream
from services.runtime.analysis_job_service import create_job
from services.session_service import get_or_create_active_session, update_session_activity


@dataclass(frozen=True)
class DreamIntakeResult:
    dream: Dream
    job: AnalysisJob


async def register_incoming_dream(db: AsyncSession, telegram_id: int, text: str) -> DreamIntakeResult:
    """Persist dream and enqueue analysis in the same database transaction."""
    active_session = await get_or_create_active_session(db, user_id=telegram_id)
    dream = await create_dream(db, user_id=telegram_id, text=text, session_id=active_session.id)
    await update_session_activity(db, active_session.id)
    job = await create_job(
        db,
        session_id=active_session.id,
        dream_id=dream.id,
        provider=settings.LLM_PROVIDER,
        model=settings.DEFAULT_MODEL,
        max_attempts=settings.ANALYSIS_JOB_MAX_ATTEMPTS,
        mode="auto",
    )
    return DreamIntakeResult(dream=dream, job=job)
