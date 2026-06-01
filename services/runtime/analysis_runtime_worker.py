# stdlib
import asyncio
from collections.abc import Awaitable, Callable
import logging
import time

# thirdparty
from sqlalchemy.ext.asyncio import AsyncSession

# project
from db.models.analysis_job_model import AnalysisJob
from services.runtime.analysis_job_service import acquire_available_jobs
from services.runtime.analysis_runtime_executor import execute_analysis_job

logger = logging.getLogger(__name__)

RuntimeExecutor = Callable[[AsyncSession, AnalysisJob], Awaitable[AnalysisJob]]


class AnalysisRuntimeWorker:
    def __init__(
        self,
        *,
        session_factory,
        worker_id: str,
        batch_size: int,
        max_concurrency: int,
        poll_interval_seconds: float,
        executor: RuntimeExecutor = execute_analysis_job,
    ) -> None:
        self.session_factory = session_factory
        self.worker_id = worker_id
        self.batch_size = max(1, batch_size)
        self.max_concurrency = max(1, max_concurrency)
        self.poll_interval_seconds = poll_interval_seconds
        self.executor = executor
        self._stopping = False

    async def stop(self) -> None:
        self._stopping = True

    async def run_forever(self) -> None:
        while not self._stopping:
            await self.run_once()
            if not self._stopping:
                await asyncio.sleep(self.poll_interval_seconds)

    async def run_once(self) -> int:
        if self._stopping:
            return 0

        async with self.session_factory.begin() as db:
            jobs = await acquire_available_jobs(
                db,
                limit=self.batch_size,
                locked_by=self.worker_id,
            )

        if not jobs:
            return 0

        logger.info(
            "Analysis runtime worker batch acquired",
            extra={
                "worker_id": self.worker_id,
                "job_ids": [str(job.id) for job in jobs],
                "batch_size": len(jobs),
            },
        )

        processed = 0
        for offset in range(0, len(jobs), self.max_concurrency):
            batch = jobs[offset : offset + self.max_concurrency]
            results = await asyncio.gather(*(self._execute(job) for job in batch), return_exceptions=True)
            processed += sum(1 for result in results if not isinstance(result, Exception))
        return processed

    async def _execute(self, job: AnalysisJob) -> AnalysisJob:
        started = time.perf_counter()
        logger.info(
            "Analysis runtime worker execution start",
            extra={
                "worker_id": self.worker_id,
                "job_id": str(job.id),
                "session_id": str(job.session_id),
                "locked_by": job.locked_by,
                "provider": job.provider,
                "model": job.model,
            },
        )
        try:
            async with self.session_factory.begin() as db:
                result = await self.executor(db, job)
        except Exception:
            duration_ms = int((time.perf_counter() - started) * 1000)
            logger.exception(
                "Analysis runtime worker execution failed",
                extra={
                    "worker_id": self.worker_id,
                    "job_id": str(job.id),
                    "duration_ms": duration_ms,
                    "final_state": job.status,
                },
            )
            raise
        duration_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "Analysis runtime worker execution end",
            extra={
                "worker_id": self.worker_id,
                "job_id": str(job.id),
                "duration_ms": duration_ms,
                "final_state": result.status,
                "locked_by": job.locked_by,
            },
        )
        return result
