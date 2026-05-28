# stdlib
from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class AnalysisJobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class RuntimeExecutionResult:
    job_id: UUID
    status: AnalysisJobStatus
    retryable: bool


class AnalysisRuntimeError(Exception):
    """Base class for runtime-layer failures."""


class InvalidJobTransitionError(AnalysisRuntimeError):
    """Raised when a job lifecycle transition violates runtime invariants."""


class RetryableAnalysisError(Exception):
    """Domain/orchestrator-classified transient failure."""


class NonRetryableAnalysisError(Exception):
    """Domain/orchestrator-classified terminal failure."""
