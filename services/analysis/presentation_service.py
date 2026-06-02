# project
from db.models.session_analysis_model import SessionAnalysis
from db.schemas.session_analysis_schema import (
    LegacyAnalysisPayloadSchema,
    SessionAnalysisItemSchema,
    SessionAnalysisSchema,
)
from services.analysis.dto.dream_analysis_legacy_mapper import LegacyMapperV1
from services.analysis.schema.dream_analysis_v1 import DreamAnalysisV1


def to_legacy_presentation(analysis_json: dict) -> LegacyAnalysisPayloadSchema:
    """Map stored canonical dream analysis JSON to legacy presentation fields."""
    canonical = DreamAnalysisV1.model_validate(analysis_json)
    legacy = LegacyMapperV1().map(canonical)
    return LegacyAnalysisPayloadSchema.model_validate(legacy.model_dump())


def build_session_analysis_schema(analysis: SessionAnalysis) -> SessionAnalysisSchema:
    return SessionAnalysisSchema(
        id=analysis.id,
        session_id=analysis.session_id,
        thread_id=analysis.thread_id,
        user_id=analysis.user_id,
        provider=analysis.provider,
        model=analysis.model,
        prompt_version=analysis.prompt_version,
        analysis_version=analysis.analysis_version,
        analysis_json=to_legacy_presentation(analysis.analysis_json),
        raw_response=analysis.raw_response,
        is_latest=analysis.is_latest,
        continuation_index=analysis.continuation_index,
        created_at=analysis.created_at,
    )


def build_session_analysis_item_schema(analysis: SessionAnalysis) -> SessionAnalysisItemSchema:
    return SessionAnalysisItemSchema(
        id=analysis.id,
        created_at=analysis.created_at,
        is_latest=analysis.is_latest,
        continuation_index=analysis.continuation_index,
        provider=analysis.provider,
        model=analysis.model,
        prompt_version=analysis.prompt_version,
        analysis_version=analysis.analysis_version,
        analysis_json=to_legacy_presentation(analysis.analysis_json),
        raw_response=analysis.raw_response,
    )
