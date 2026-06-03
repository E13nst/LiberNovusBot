# stdlib
import uuid

# thirdparty
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.sql import func

# project
from db.db_setup import Base


class DreamMemory(Base):
    __tablename__ = "dream_memories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dream_id = Column(
        Integer,
        ForeignKey("dreams.id"),
        nullable=False,
        index=True,
        unique=True,
        comment="One structured memory blob per dream",
    )
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dream_sessions.id"),
        nullable=False,
        index=True,
    )
    user_id = Column(BigInteger, nullable=False, index=True)
    memory_version = Column(String, nullable=False, default="structured_dream_v1")
    memory_json = Column(JSON, nullable=False)
    analysis_job_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
