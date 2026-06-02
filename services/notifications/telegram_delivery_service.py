# stdlib
import logging

# thirdparty
import httpx

# project
import settings
from db.models.session_analysis_model import SessionAnalysis
from services.analysis.schema.dream_analysis_v1 import DreamAnalysisV1

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"


def format_analysis_message(analysis: SessionAnalysis) -> str:
    """Format persisted canonical analysis for Telegram delivery (presentation only)."""
    canonical = DreamAnalysisV1.model_validate(analysis.analysis_json or {})
    key_thought = canonical.summary.strip() or canonical.narrative_interpretation.strip()

    symbol_lines = [
        f"- {item.symbol} → {item.meaning}" for item in canonical.symbols
    ] or ["—"]
    archetype_lines = [f"- {name}" for name in canonical.jungian_interpretation.archetypes] or ["—"]

    return (
        "🧠 Анализ сна\n\n"
        f"🪞 Ключевая мысль:\n{key_thought}\n\n"
        "🌊 Символы:\n"
        f"{chr(10).join(symbol_lines)}\n\n"
        "🌓 Архетипы:\n"
        f"{chr(10).join(archetype_lines)}\n\n"
        f"💡 Главный инсайт:\n{canonical.key_insight}"
    )


class TelegramDeliveryService:
    """Send formatted analysis via Telegram Bot API; no analysis business logic."""

    def __init__(self, *, bot_token: str | None = None, http_client: httpx.AsyncClient | None = None) -> None:
        self._bot_token = bot_token if bot_token is not None else settings.BOT_TOKEN
        self._http_client = http_client

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
