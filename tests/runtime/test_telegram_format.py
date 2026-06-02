# thirdparty
import pytest

# project
from db.models.session_analysis_model import SessionAnalysis
from services.notifications.telegram_delivery_service import format_analysis_message
from tests.fixtures.dream_analysis_v1 import sample_dream_analysis_v1_json


def test_format_analysis_message_uses_structured_dream_v1_sections():
    analysis = SessionAnalysis(
        session_id="11111111-1111-1111-1111-111111111111",
        thread_id="22222222-2222-2222-2222-222222222222",
        user_id=123,
        provider="mock",
        model="mock-v1",
        prompt_version="v1",
        analysis_version="dream_v1",
        analysis_json=sample_dream_analysis_v1_json(),
    )

    message = format_analysis_message(analysis)

    assert "🧠 Анализ сна" in message
    assert "🪞 Ключевая мысль:" in message
    assert "🌊 Символы:" in message
    assert "water →" in message
    assert "🌓 Архетипы:" in message
    assert "shadow" in message
    assert "💡 Главный инсайт:" in message


def test_format_analysis_message_rejects_invalid_payload():
    analysis = SessionAnalysis(
        session_id="11111111-1111-1111-1111-111111111111",
        thread_id="22222222-2222-2222-2222-222222222222",
        user_id=123,
        provider="mock",
        model="mock-v1",
        prompt_version="v1",
        analysis_version="dream_v1",
        analysis_json={"interpretation": "legacy"},
    )

    with pytest.raises(Exception):
        format_analysis_message(analysis)
