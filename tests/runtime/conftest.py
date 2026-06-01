# stdlib
import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

# thirdparty
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

# project
from db.models.analysis_job_model import AnalysisJob
from db.models.dream_model import Dream
from db.models.session_model import DreamSession
from db.models.session_summary_model import SessionSummary
from services.analysis_policy import utc_now
from services.runtime.analysis_job_service import create_job, mark_completed
from services.runtime.runtime_types import AnalysisJobStatus


@dataclass
class ExecutionTracker:
    execution_counts: dict[UUID, int] = field(default_factory=lambda: defaultdict(int))
    provider_call_counts: dict[UUID, int] = field(default_factory=lambda: defaultdict(int))
    active_windows: dict[UUID, list[tuple[datetime, datetime | None]]] = field(default_factory=lambda: defaultdict(list))
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def record_execution_start(self, job_id: UUID) -> None:
        async with self._lock:
            self.execution_counts[job_id] += 1
            self.active_windows[job_id].append((utc_now(), None))

    async def record_execution_end(self, job_id: UUID) -> None:
        async with self._lock:
            windows = self.active_windows[job_id]
            if windows and windows[-1][1] is None:
                start, _ = windows[-1]
                windows[-1] = (start, utc_now())

    async def record_provider_call(self, job_id: UUID) -> None:
        async with self._lock:
            self.provider_call_counts[job_id] += 1

    def assert_single_execution_per_job(self, job_ids: list[UUID]) -> None:
        for job_id in job_ids:
            assert self.execution_counts[job_id] == 1, (
                f"job {job_id}: expected 1 execution, got {self.execution_counts[job_id]}"
            )

    def assert_single_provider_call_per_job(self, job_ids: list[UUID]) -> None:
        for job_id in job_ids:
            assert self.provider_call_counts[job_id] == 1, (
                f"job {job_id}: expected 1 provider call, got {self.provider_call_counts[job_id]}"
            )

    def assert_no_overlapping_windows(self, job_ids: list[UUID]) -> None:
        for job_id in job_ids:
            windows = self.active_windows[job_id]
            closed = [(s, e) for s, e in windows if e is not None]
            for i, (start_a, end_a) in enumerate(closed):
                for start_b, end_b in closed[i + 1 :]:
                    overlap = start_a < end_b and start_b < end_a
                    assert not overlap, f"job {job_id}: overlapping execution windows"


@pytest.fixture
def execution_tracker() -> ExecutionTracker:
    return ExecutionTracker()


async def seed_queued_jobs(
    session_factory,
    user_id: int,
    count: int,
    *,
    session_id: UUID | None = None,
    max_attempts: int = 1,
) -> tuple[UUID, list[UUID]]:
    async with session_factory.begin() as db:
        if session_id is None:
            session = DreamSession(user_id=user_id, status="active")
            db.add(session)
            await db.flush()
            session_id = session.id
        job_ids = []
        for _ in range(count):
            job = await create_job(
                db,
                session_id=session_id,
                provider="mock",
                model="mock-v1",
                max_attempts=max_attempts,
            )
            job_ids.append(job.id)
        return session_id, job_ids


async def seed_analysis_ready_session(session_factory, user_id: int) -> UUID:
    async with session_factory.begin() as db:
        session = DreamSession(user_id=user_id, status="active")
        db.add(session)
        await db.flush()
        db.add(
            SessionSummary(
                session_id=session.id,
                user_id=user_id,
                dream_count=1,
                key_symbols=["water"],
                recurring_words=[],
                raw_text_sample="river and bridge",
            )
        )
        db.add(
            Dream(user_id=user_id, text="I crossed a bridge over dark water", session_id=session.id)
        )
        await db.flush()
        return session.id


async def load_jobs(session_factory, job_ids: list[UUID]) -> list[AnalysisJob]:
    async with session_factory() as db:
        result = await db.execute(select(AnalysisJob).where(AnalysisJob.id.in_(job_ids)))
        by_id = {job.id: job for job in result.scalars().all()}
        return [by_id[jid] for jid in job_ids]


async def assert_all_jobs_terminal(session_factory, job_ids: list[UUID]) -> None:
    jobs = await load_jobs(session_factory, job_ids)
    terminal = {AnalysisJobStatus.COMPLETED.value, AnalysisJobStatus.FAILED.value}
    for job in jobs:
        assert job.status in terminal, f"job {job.id} stuck in {job.status}"


def assert_no_duplicate_active_execution(tracker: ExecutionTracker, job_ids: list[UUID]) -> None:
    tracker.assert_single_execution_per_job(job_ids)
    tracker.assert_no_overlapping_windows(job_ids)


def make_tracking_executor(
    tracker: ExecutionTracker,
    *,
    delay_seconds: float = 0.0,
    provider_calls: bool = True,
    on_execute=None,
):
    async def _executor(db: AsyncSession, job: AnalysisJob):
        await tracker.record_execution_start(job.id)
        if provider_calls:
            await tracker.record_provider_call(job.id)
        if delay_seconds:
            await asyncio.sleep(delay_seconds)
        if on_execute is not None:
            result = on_execute(job)
            if asyncio.iscoroutine(result):
                result = await result
            if result is not None:
                await tracker.record_execution_end(job.id)
                return result
        completed = await mark_completed(db, job.id, thread_id=None)
        await tracker.record_execution_end(job.id)
        return completed

    return _executor


async def count_session_analyses(session_factory, session_id: UUID) -> int:
    from db.models.session_analysis_model import SessionAnalysis

    async with session_factory() as db:
        return await db.scalar(
            select(func.count()).select_from(SessionAnalysis).where(SessionAnalysis.session_id == session_id)
        )
