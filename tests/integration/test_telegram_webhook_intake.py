# thirdparty
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

# project
from db.models.analysis_job_model import AnalysisJob
from db.models.dream_model import Dream
from services.runtime.runtime_types import AnalysisJobStatus
from tests.support.telegram_updates import make_telegram_update

pytestmark = pytest.mark.integration

E2E_DREAM_TEXT = "Мне снился океан и разрушенный город с высокими волнами"


class RecordingTelegramDelivery:
    def __init__(self) -> None:
        self.chat_actions: list[tuple[str, str]] = []
        self.sent_texts: list[tuple[str, str]] = []

    async def send_chat_action(self, chat_id: str, action: str = "typing") -> None:
        self.chat_actions.append((chat_id, action))

    async def send_text(self, chat_id: str, text: str) -> None:
        self.sent_texts.append((chat_id, text))


async def test_telegram_webhook_creates_dream_and_queued_job(api_client, db_engine, user_id):
    response = await api_client.post(
        "/telegram/webhook",
        json=make_telegram_update(text=E2E_DREAM_TEXT, user_id=user_id),
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}

    session_factory = sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        dream_count = await db.scalar(select(func.count()).select_from(Dream).where(Dream.user_id == user_id))
        job_count = await db.scalar(select(func.count()).select_from(AnalysisJob))
        job = await db.scalar(select(AnalysisJob).limit(1))

    assert dream_count == 1
    assert job_count == 1
    assert job is not None
    assert job.status == AnalysisJobStatus.QUEUED.value


async def test_telegram_webhook_dialogue_reply_does_not_inject_display_name_prefix(api_client, db_engine, user_id):
    response = await api_client.post(
        "/telegram/webhook",
        json=make_telegram_update(
            text=E2E_DREAM_TEXT,
            user_id=user_id,
            first_name="Анна",
            language_code="ru",
        ),
    )

    assert response.status_code == 200

    from db.models.conversation_turn_model import ConversationTurn
    from sqlalchemy import select

    session_factory = sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        assistant_turn = await db.scalar(
            select(ConversationTurn)
            .where(ConversationTurn.user_id == user_id, ConversationTurn.role == "assistant")
            .order_by(ConversationTurn.created_at.desc())
            .limit(1)
        )

    assert assistant_turn is not None
    assert not assistant_turn.text.startswith("Анна,")
    assert not assistant_turn.text.startswith("Анна, ")


async def test_telegram_webhook_short_unclear_message_routes_to_clarification_without_enqueue(
    api_client,
    db_engine,
    user_id,
):
    response = await api_client.post(
        "/telegram/webhook",
        json=make_telegram_update(text="вода", user_id=user_id),
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}

    session_factory = sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        dream_count = await db.scalar(select(func.count()).select_from(Dream).where(Dream.user_id == user_id))
        job_count = await db.scalar(select(func.count()).select_from(AnalysisJob))

    assert dream_count == 0
    assert job_count == 0


async def test_telegram_webhook_sends_typing_before_ingress(api_client, user_id, monkeypatch):
    recording = RecordingTelegramDelivery()
    ingress_started = {"value": False}

    async def track_ingress(*args, **kwargs):
        assert recording.chat_actions == [(str(user_id), "typing")]
        ingress_started["value"] = True
        from services.ingress.ingress_service import process_incoming_message as real_process

        return await real_process(*args, **kwargs)

    monkeypatch.setattr(
        "routers.telegram_webhook.TelegramDeliveryService",
        lambda: recording,
    )
    monkeypatch.setattr("routers.telegram_webhook.process_incoming_message", track_ingress)

    response = await api_client.post(
        "/telegram/webhook",
        json=make_telegram_update(text=E2E_DREAM_TEXT, user_id=user_id),
    )

    assert response.status_code == 200
    assert ingress_started["value"] is True
    assert recording.chat_actions == [(str(user_id), "typing")]
