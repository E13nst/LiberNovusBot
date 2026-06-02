#!/usr/bin/env python3
"""Remove legacy session pipeline data created before policy trace observability.

Targets dream_sessions that have zero dialogue_policy_traces rows. Deletes related
dreams, jobs, analyses, threads, and summaries in FK-safe order.
"""

from __future__ import annotations

import argparse
import asyncio
from uuid import UUID

from sqlalchemy import delete, exists, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from db.models.analysis_job_model import AnalysisJob
from db.models.analysis_thread_model import AnalysisThread
from db.models.dialogue_policy_trace_model import DialoguePolicyTrace
from db.models.dream_model import Dream
from db.models.session_analysis_model import SessionAnalysis
from db.models.session_model import DreamSession
from db.models.session_summary_model import SessionSummary
from settings import DATABASE_URL


async def _legacy_session_ids(db: AsyncSession) -> list[UUID]:
    has_trace = exists().where(DialoguePolicyTrace.session_id == DreamSession.id)
    rows = await db.execute(select(DreamSession.id).where(~has_trace))
    return list(rows.scalars().all())


async def _count_for_sessions(db: AsyncSession, session_ids: list[UUID]) -> dict[str, int]:
    if not session_ids:
        return {
            "sessions": 0,
            "dreams": 0,
            "jobs": 0,
            "analyses": 0,
            "threads": 0,
            "summaries": 0,
            "policy_traces": 0,
        }

    async def count(model, column):
        result = await db.execute(select(func.count()).select_from(model).where(column.in_(session_ids)))
        return int(result.scalar_one())

    return {
        "sessions": len(session_ids),
        "dreams": await count(Dream, Dream.session_id),
        "jobs": await count(AnalysisJob, AnalysisJob.session_id),
        "analyses": await count(SessionAnalysis, SessionAnalysis.session_id),
        "threads": await count(AnalysisThread, AnalysisThread.session_id),
        "summaries": await count(SessionSummary, SessionSummary.session_id),
        "policy_traces": await count(DialoguePolicyTrace, DialoguePolicyTrace.session_id),
    }


async def cleanup_legacy_sessions(*, execute: bool) -> dict[str, int]:
    engine = create_async_engine(DATABASE_URL)
    session_factory = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        session_ids = await _legacy_session_ids(db)
        preview = await _count_for_sessions(db, session_ids)

        if not session_ids:
            await engine.dispose()
            return preview

        if not execute:
            await engine.dispose()
            return preview

        await db.execute(
            delete(DialoguePolicyTrace).where(DialoguePolicyTrace.session_id.in_(session_ids))
        )
        await db.execute(
            update(AnalysisThread)
            .where(AnalysisThread.session_id.in_(session_ids))
            .values(last_analysis_id=None)
        )
        await db.execute(delete(SessionAnalysis).where(SessionAnalysis.session_id.in_(session_ids)))
        await db.execute(delete(AnalysisJob).where(AnalysisJob.session_id.in_(session_ids)))
        await db.execute(delete(AnalysisThread).where(AnalysisThread.session_id.in_(session_ids)))
        await db.execute(delete(SessionSummary).where(SessionSummary.session_id.in_(session_ids)))
        await db.execute(delete(Dream).where(Dream.session_id.in_(session_ids)))
        await db.execute(delete(DreamSession).where(DreamSession.id.in_(session_ids)))
        await db.commit()

    await engine.dispose()
    return preview


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Apply deletions. Without this flag, only print what would be removed.",
    )
    args = parser.parse_args()

    counts = asyncio.run(cleanup_legacy_sessions(execute=args.execute))

    mode = "DELETE" if args.execute else "DRY RUN"
    print(f"[{mode}] Legacy sessions cleanup (sessions without policy traces)")
    for key, value in counts.items():
        print(f"  {key}: {value}")

    if not args.execute and counts["sessions"] > 0:
        print("\nRe-run with --execute to apply.")


if __name__ == "__main__":
    main()
