# stdlib
import uuid

# thirdparty
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

# project
from db.db_setup import Base


class SessionSummary(Base):
    __tablename__ = "session_summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dream_sessions.id"),
        nullable=False,
        unique=True,
        index=True,
        comment="Dream session ID",
    )
    user_id = Column(BigInteger, nullable=False, index=True, comment="Telegram user ID")
    dream_count = Column(Integer, nullable=False, comment="Number of dreams in session")
    key_symbols = Column(JSON, nullable=False, comment="Top rule-based symbols")
    recurring_words = Column(JSON, nullable=False, comment="Words appearing in multiple dreams")
    raw_text_sample = Column(Text, nullable=True, comment="Truncated sample of dream text")
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment="Created At")
