# stdlib
import logging
from typing import Protocol

# project
from db.models.analysis_job_model import AnalysisJob
from db.models.session_analysis_model import SessionAnalysis
from services.notifications.delivery_lock_service import acquire_delivery_lock
from services.notifications.telegram_delivery_service import TelegramDeliveryService
from services.runtime.runtime_types import AnalysisJobStatus

logger = logging.getLogger(__name__)


def _analysis_id(analysis: SessionAnalysis) -> str | None:
    value = getattr(analysis, "id", None)
    return str(value) if value is not None else None


def _chat_id(analysis: SessionAnalysis) -> str | None:
    value = getattr(analysis, "user_id", None)
    return str(value) if value is not None else None


class TelegramDeliveryPort(Protocol):
    async def send_analysis(self, chat_id: str, analysis: SessionAnalysis) -> None: ...


async def deliver_completed_analysis(
    job: AnalysisJob,
    analysis: SessionAnalysis,
    *,
    redis_client,
    telegram_delivery: TelegramDeliveryPort | TelegramDeliveryService,
) -> bool:
    """Best-effort Telegram delivery after job completion; does not mutate job state."""
    if job.status != AnalysisJobStatus.COMPLETED.value:
        logger.info(
            "Analysis delivery skipped",
            extra={
                "job_id": str(job.id),
                "session_id": str(job.session_id),
                "analysis_id": _analysis_id(analysis),
                "delivery_success": False,
                "delivery_skip_reason": "job_not_completed",
            },
        )
        return False

    analysis_job_id = getattr(analysis, "analysis_job_id", None)
    if analysis_job_id != job.id:
        logger.info(
            "Analysis delivery skipped",
            extra={
                "job_id": str(job.id),
                "session_id": str(job.session_id),
                "analysis_id": _analysis_id(analysis),
                "delivery_success": False,
                "delivery_skip_reason": "analysis_job_mismatch",
            },
        )
        return False

    acquired = await acquire_delivery_lock(redis_client, str(job.id))
    if not acquired:
        logger.info(
            "Analysis delivery skipped",
            extra={
                "job_id": str(job.id),
                "session_id": str(job.session_id),
                "analysis_id": _analysis_id(analysis),
                "chat_id": _chat_id(analysis),
                "delivery_success": False,
                "delivery_skip_reason": "lock_exists",
            },
        )
        return False

    chat_id = _chat_id(analysis)
    if chat_id is None:
        logger.info(
            "Analysis delivery skipped",
            extra={
                "job_id": str(job.id),
                "session_id": str(job.session_id),
                "analysis_id": _analysis_id(analysis),
                "delivery_success": False,
                "delivery_skip_reason": "missing_chat_id",
            },
        )
        return False

    try:
        await telegram_delivery.send_analysis(chat_id, analysis)
    except Exception:
        logger.exception(
            "Analysis delivery failed",
            extra={
                "job_id": str(job.id),
                "session_id": str(job.session_id),
                "analysis_id": _analysis_id(analysis),
                "chat_id": chat_id,
                "delivery_success": False,
            },
        )
        return False

    logger.info(
        "Analysis delivery completed",
        extra={
            "job_id": str(job.id),
            "session_id": str(job.session_id),
            "analysis_id": _analysis_id(analysis),
            "chat_id": chat_id,
            "delivery_success": True,
        },
    )
    return True
