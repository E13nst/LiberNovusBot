import uuid

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from db.db_setup import Base


class DialoguePolicyTrace(Base):
    __tablename__ = "dialogue_policy_traces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(BigInteger, nullable=False, index=True, comment="Telegram user ID")
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dream_sessions.id"),
        nullable=True,
        index=True,
        comment="Resolved session for stateful reflection routes",
    )
    dream_id = Column(
        Integer,
        ForeignKey("dreams.id"),
        nullable=True,
        index=True,
        comment="Dream row created by reflection route, if any",
    )
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("analysis_jobs.id"),
        nullable=True,
        index=True,
        comment="Analysis job enqueued by reflection route, if any",
    )
    input_json = Column(JSON, nullable=False, comment="PolicyInput projection without raw text")
    decision_json = Column(JSON, nullable=False, comment="PolicyDecision projection")
    route = Column(String, nullable=False, index=True)
    reason_code = Column(String, nullable=False)
    outcome_json = Column(JSON, nullable=False, comment="Execution outcome projection")
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment="Created At")
