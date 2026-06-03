# thirdparty
import pytest
from sqlalchemy import func, select

# project
from db.models.analysis_job_model import AnalysisJob
from db.models.conversation_turn_model import ConversationTurn
from db.models.dream_model import Dream
from services.ingress.ingress_service import process_incoming_message

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_ingress_new_dream_creates_dream_turn_and_job(db_session, user_id):
    text = "Мне снился длинный сон про отца, деменцию и страх уехать в другой город"
    result = await process_incoming_message(db_session, telegram_id=user_id, text=text)

    assert result.outbound_messages
    dream_count = await db_session.scalar(select(func.count()).select_from(Dream).where(Dream.user_id == user_id))
    turn_count = await db_session.scalar(
        select(func.count()).select_from(ConversationTurn).where(ConversationTurn.user_id == user_id)
    )
    job_count = await db_session.scalar(select(func.count()).select_from(AnalysisJob))

    assert dream_count == 1
    assert turn_count >= 2
    assert job_count == 1


@pytest.mark.asyncio
async def test_ingress_dialogue_reply_does_not_inject_display_name_prefix(db_session, user_id):
    text = "Мне снился длинный сон про отца, деменцию и страх уехать в другой город"
    result = await process_incoming_message(
        db_session,
        telegram_id=user_id,
        text=text,
        user_display_name="Анна",
        user_language_code="ru",
    )

    assert result.outbound_messages
    reply = result.outbound_messages[0]
    assert not reply.startswith("Анна,")
    assert not reply.startswith("Анна, ")


@pytest.mark.asyncio
async def test_ingress_clarification_does_not_use_display_name(db_session, user_id):
    result = await process_incoming_message(
        db_session,
        telegram_id=user_id,
        text="вода",
        user_display_name="Анна",
    )

    assert result.outbound_messages
    reply = result.outbound_messages[0]
    assert "Анна" not in reply


@pytest.mark.asyncio
async def test_ingress_follow_up_is_dialogue_without_new_dream(db_session, user_id):
    await process_incoming_message(
        db_session,
        telegram_id=user_id,
        text="Мне снился длинный сон про отца, деменцию и страх уехать в другой город",
    )
    result = await process_incoming_message(
        db_session,
        telegram_id=user_id,
        text="отец умер два года назад",
    )

    dream_count = await db_session.scalar(select(func.count()).select_from(Dream).where(Dream.user_id == user_id))
    assert dream_count == 1
    assert result.outbound_messages
