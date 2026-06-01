# stdlib
from dataclasses import dataclass
from typing import Any
from uuid import UUID

# project
from db.models.analysis_thread_model import AnalysisThread


@dataclass(frozen=True)
class SessionAnalysisPrepareResult:
    """Validated analysis payload and thread target before persistence."""

    thread: AnalysisThread
    session_id: UUID
    user_id: int
    provider: str
    model: str
    prompt_version: str
    analysis_version: str
    analysis_json: dict[str, Any]
    raw_response: str | None
