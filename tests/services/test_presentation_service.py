# stdlib
from datetime import datetime
from uuid import uuid4

# project
from db.models.session_analysis_model import SessionAnalysis
from services.analysis.presentation_service import (
    build_session_analysis_item_schema,
    build_session_analysis_schema,
    to_legacy_presentation,
)
from tests.fixtures.dream_analysis_v1 import sample_dream_analysis_v1_json


def test_to_legacy_presentation_maps_canonical_to_legacy_fields():
    legacy = to_legacy_presentation(sample_dream_analysis_v1_json())

    assert legacy.interpretation
    assert "water" in legacy.themes
    assert legacy.questions_for_user


def test_build_session_analysis_schema_exposes_legacy_payload():
    analysis = SessionAnalysis(
        id=uuid4(),
        session_id=uuid4(),
        thread_id=uuid4(),
        user_id=123,
        provider="mock",
        model="mock-v1",
        prompt_version="v1",
        analysis_version="dream_v1",
        analysis_json=sample_dream_analysis_v1_json(),
        is_latest=True,
        continuation_index=0,
        created_at=datetime.utcnow(),
    )

    schema = build_session_analysis_schema(analysis)

    assert schema.analysis_version == "dream_v1"
    assert schema.analysis_json.interpretation
    assert "water" in schema.analysis_json.themes


def test_build_session_analysis_item_schema_exposes_legacy_payload():
    analysis = SessionAnalysis(
        id=uuid4(),
        session_id=uuid4(),
        thread_id=uuid4(),
        user_id=123,
        provider="mock",
        model="mock-v1",
        prompt_version="v1",
        analysis_version="dream_v1",
        analysis_json=sample_dream_analysis_v1_json(),
        is_latest=True,
        continuation_index=0,
        created_at=datetime.utcnow(),
    )

    item = build_session_analysis_item_schema(analysis)

    assert item.analysis_json.interpretation
    assert item.analysis_json.questions_for_user
