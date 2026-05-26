# thirdparty
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

# project
from db.db_setup import Base


class Dream(Base):
    __tablename__ = "dreams"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, comment="Telegram user ID")
    text = Column(Text, nullable=False, comment="Dream text")
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment="Created At")
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dream_sessions.id"),
        nullable=False,
        index=True,
        comment="Dream session ID",
    )

    session = relationship("DreamSession", back_populates="dreams")
