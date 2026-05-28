# stdlib
import uuid

# thirdparty
from sqlalchemy import Column, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

# project
from db.db_setup import Base

THREAD_STATUS_ACTIVE = "active"
THREAD_STATUS_IDLE = "idle"
THREAD_STATUS_CLOSED = "closed"
# Legacy alias kept for migration/backfill references only.
THREAD_STATUS_SUPERSEDED = THREAD_STATUS_IDLE
THREAD_STATUS_COMPLETED = THREAD_STATUS_CLOSED


class AnalysisThread(Base):
    __tablename__ = "analysis_threads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dream_sessions.id"),
        nullable=False,
        index=True,
        comment="Dream session ID",
    )
    status = Column(
        String,
        nullable=False,
        comment="Thread status: active, idle, closed",
    )
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment="Created At")
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), comment="Updated At")
    last_activity_at = Column(
        DateTime,
        nullable=True,
        comment="Updated only when analysis is persisted for this thread",
    )
    last_analysis_id = Column(
        UUID(as_uuid=True),
        ForeignKey("session_analyses.id", use_alter=True, name="fk_analysis_threads_last_analysis"),
        nullable=True,
        comment="Most recent analysis in this thread",
    )

    __table_args__ = (
        Index("ix_analysis_threads_session_id_status", "session_id", "status"),
        Index(
            "ix_analysis_threads_one_active_per_session",
            "session_id",
            unique=True,
            postgresql_where=(status == THREAD_STATUS_ACTIVE),
        ),
    )
