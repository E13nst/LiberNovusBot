# stdlib
import uuid

# thirdparty
from sqlalchemy import BigInteger, Column, DateTime, String
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

# project
from db.db_setup import Base


class DreamSession(Base):
    __tablename__ = "dream_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(BigInteger, nullable=False, index=True, comment="Telegram user ID")
    status = Column(String, nullable=False, comment="Session status: active, closed")
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment="Created At")
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), comment="Updated At")
    last_activity_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="Last activity timestamp; used for inactivity-based auto-close",
    )

    dreams = relationship("Dream", back_populates="session")
