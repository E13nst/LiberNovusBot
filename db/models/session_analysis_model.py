# stdlib
import uuid
from uuid import UUID

# thirdparty
from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

# project
from db.db_setup import Base


class SessionAnalysis(Base):
    __tablename__ = "session_analyses"

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
        nullable=False,
        index=True,
        comment="Analysis thread ID",
    )
    user_id = Column(BigInteger, nullable=False, index=True, comment="Telegram user ID")
    provider = Column(String, nullable=False, comment="LLM provider identifier, e.g. mock")
    model = Column(String, nullable=False, comment="Model identifier, e.g. mock-v1")
    prompt_version = Column(String, nullable=False, comment="Prompt contract version used")
    analysis_version = Column(String, nullable=False, comment="Analysis output schema version")
    analysis_json = Column(JSON, nullable=False, comment="Validated structured analysis output")
    raw_response = Column(Text, nullable=True, comment="Optional raw provider response")
    is_latest = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="UI default flag within thread; write-path only",
    )
    continuation_index = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Zero-based index of analysis within thread",
    )
    analysis_job_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Runtime analysis job that produced this analysis; executor-owned trace link",
    )
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment="Created At")

    __table_args__ = (
        Index(
            "ix_session_analyses_one_latest_per_thread",
            "thread_id",
            unique=True,
            postgresql_where=(is_latest.is_(True)),
        ),
        Index("ix_session_analyses_session_id_created_at", "session_id", "created_at"),
    )

    def with_job_id(self, job_id: UUID) -> "SessionAnalysis":
        """Return an assembled row copy with executor trace link; write-once before persistence."""
        if self.analysis_job_id is not None and self.analysis_job_id != job_id:
            raise ValueError(
                f"analysis_job_id already bound to {self.analysis_job_id}, cannot bind to {job_id}"
            )
        if self.analysis_job_id == job_id:
            return self
        return SessionAnalysis(
            id=self.id,
            session_id=self.session_id,
            thread_id=self.thread_id,
            user_id=self.user_id,
            provider=self.provider,
            model=self.model,
            prompt_version=self.prompt_version,
            analysis_version=self.analysis_version,
            analysis_json=self.analysis_json,
            raw_response=self.raw_response,
            is_latest=self.is_latest,
            continuation_index=self.continuation_index,
            analysis_job_id=job_id,
        )
