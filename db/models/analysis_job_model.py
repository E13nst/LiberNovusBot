# stdlib
import uuid

# thirdparty
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

# project
from db.db_setup import Base

JOB_STATUS_QUEUED = "queued"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_COMPLETED = "completed"
JOB_STATUS_FAILED = "failed"
JOB_STATUS_CANCELLED = "cancelled"


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dream_sessions.id"),
        nullable=False,
        index=True,
        comment="Dream session ID",
    )
    thread_id = Column(
        UUID(as_uuid=True),
        ForeignKey("analysis_threads.id"),
        nullable=True,
        index=True,
        comment="Resolved analysis thread ID after successful execution",
    )
    status = Column(
        String,
        nullable=False,
        index=True,
        comment="Job status: queued, running, completed, failed, cancelled",
    )
    provider = Column(String, nullable=False, comment="LLM provider identifier requested at enqueue time")
    model = Column(String, nullable=False, comment="Model identifier requested at enqueue time")
    mode = Column(String, nullable=False, default="auto", server_default="auto", comment="Analysis mode request")
    attempts = Column(Integer, nullable=False, default=0, server_default="0", comment="Execution attempt count")
    max_attempts = Column(Integer, nullable=False, default=1, server_default="1", comment="Maximum execution attempts")
    last_error_class = Column(String, nullable=True, comment="Last runtime/domain error class")
    last_error_message = Column(Text, nullable=True, comment="Last sanitized runtime/domain error message")
    retryable = Column(Boolean, nullable=False, default=False, server_default="false", comment="Last failure retryability")
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment="Created At")
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), comment="Updated At")
    available_after = Column(DateTime, nullable=False, server_default=func.now(), comment="Earliest acquisition time")
    started_at = Column(DateTime, nullable=True, comment="First execution start timestamp")
    completed_at = Column(DateTime, nullable=True, comment="Terminal completion timestamp")
    locked_by = Column(String, nullable=True, comment="Runtime worker lock owner")
    locked_at = Column(DateTime, nullable=True, comment="Runtime worker lock timestamp")

    __table_args__ = (
        Index("ix_analysis_jobs_status_available_after_created_at", "status", "available_after", "created_at"),
        Index(
            "ix_analysis_jobs_queued_available",
            "available_after",
            "created_at",
            "id",
            postgresql_where=(status == JOB_STATUS_QUEUED),
        ),
    )
