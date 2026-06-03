# stdlib
import logging

# thirdparty
import httpx

# project
import settings
from db.models.session_analysis_model import SessionAnalysis
from services.analysis.schema.dream_analysis_v1 import DreamAnalysisV1
from services.reflection.dream_reflection_transformer import DreamReflectionTransformer

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"


def format_analysis_message(analysis: SessionAnalysis) -> str:
    """Legacy session-analysis report formatter (admin/debug paths only; not primary bot UX)."""
    canonical = DreamAnalysisV1.model_validate(analysis.analysis_json or {})
    reflection = DreamReflectionTransformer().transform(canonical)

    return (
        "🧠 Анализ сна\n\n"
        "1) Структура сна\n"
        f"{_render_lines(reflection.dream_structure)}\n\n"
        "2) Возможные направления осмысления\n"
        f"{_render_lines(reflection.reflection_directions)}\n\n"
        "3) Вопросы пользователю\n"
        f"{_render_lines([f'- {item}' for item in reflection.questions])}\n\n"
        "4) Контекст сна\n"
        f"{_render_lines(reflection.dream_context)}"
    )


def _render_lines(lines: list[str]) -> str:
    return "\n".join(lines) if lines else "—"


class TelegramDeliveryService:
    """Send formatted analysis via Telegram Bot API; no analysis business logic."""

    def __init__(self, *, bot_token: str | None = None, http_client: httpx.AsyncClient | None = None) -> None:
        self._bot_token = bot_token if bot_token is not None else settings.BOT_TOKEN
        self._http_client = http_client

    async def send_text(self, chat_id: str, text: str) -> None:
        if not self._bot_token:
            raise RuntimeError("BOT_TOKEN is not configured")

        url = f"{TELEGRAM_API_BASE}/bot{self._bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text}

        if self._http_client is not None:
            response = await self._http_client.post(url, json=payload, timeout=10.0)
        else:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10.0)

        response.raise_for_status()

    async def send_analysis(self, chat_id: str, analysis: SessionAnalysis) -> None:
        if not self._bot_token:
            raise RuntimeError("BOT_TOKEN is not configured")

        message = format_analysis_message(analysis)
        url = f"{TELEGRAM_API_BASE}/bot{self._bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message}

        if self._http_client is not None:
            response = await self._http_client.post(url, json=payload, timeout=10.0)
        else:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10.0)

        response.raise_for_status()
        logger.info(
            "Telegram analysis delivery sent",
            extra={
                "chat_id": chat_id,
                "analysis_id": str(analysis.id) if analysis.id else None,
                "session_id": str(analysis.session_id),
            },
        )
