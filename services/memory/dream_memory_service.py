# stdlib
from typing import Any
from uuid import UUID

# thirdparty
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# project
from db.models.dream_memory_model import DreamMemory
from services.analysis.schema.structured_dream_memory_v1 import StructuredDreamMemoryV1

MEMORY_VERSION = "structured_dream_v1"


async def upsert_dream_memory(
    db: AsyncSession,
    *,
    dream_id: int,
    session_id: UUID,
    user_id: int,
    memory: StructuredDreamMemoryV1,
    analysis_job_id: UUID | None = None,
) -> DreamMemory:
    existing = await db.scalar(select(DreamMemory).where(DreamMemory.dream_id == dream_id))
    payload = memory.model_dump()
    if existing is None:
        row = DreamMemory(
            dream_id=dream_id,
            session_id=session_id,
            user_id=user_id,
            memory_version=MEMORY_VERSION,
            memory_json=payload,
            analysis_job_id=analysis_job_id,
        )
        db.add(row)
        await db.flush()
        return row

    existing.memory_json = payload
    existing.memory_version = MEMORY_VERSION
    if analysis_job_id is not None:
        existing.analysis_job_id = analysis_job_id
    await db.flush()
    return existing


async def get_dream_memory(db: AsyncSession, dream_id: int) -> DreamMemory | None:
    return await db.scalar(select(DreamMemory).where(DreamMemory.dream_id == dream_id))


def dream_analysis_v1_to_memory(payload: dict[str, Any]) -> StructuredDreamMemoryV1:
    """Map legacy DreamAnalysisV1-shaped JSON into stage-shaped memory (v1 bridge)."""
    symbols = payload.get("symbols") or []
    amplification = [
        {
            "symbol": item.get("symbol", ""),
            "personal": item.get("meaning", ""),
            "cultural": "",
            "archetypal": "",
        }
        for item in symbols
        if isinstance(item, dict)
    ]
    emotional = payload.get("emotional_state") or {}
    emotional_field: list[str] = []
    if isinstance(emotional, dict):
        primary = emotional.get("primary", "")
        secondary = emotional.get("secondary", "")
        if primary:
            emotional_field.append(str(primary))
        if secondary:
            emotional_field.append(str(secondary))

    jungian = payload.get("jungian_interpretation") or {}
    motifs = list(jungian.get("archetypes") or []) if isinstance(jungian, dict) else []

    return StructuredDreamMemoryV1(
        dream_details=[str(payload.get("summary", "")).strip()] if payload.get("summary") else [],
        dream_ego_activity=[],
        figures=[],
        emotional_field=emotional_field,
        personal_context_questions=list(payload.get("uncertainty_notes") or []),
        amplification_candidates=amplification,
        compensation_hypotheses=[str(payload.get("narrative_interpretation", "")).strip()]
        if payload.get("narrative_interpretation")
        else [],
        open_questions=list(payload.get("uncertainty_notes") or []),
        recurring_motifs=[item.get("symbol", "") for item in symbols if isinstance(item, dict)],
        uncertainty_notes=list(payload.get("uncertainty_notes") or []),
    )
