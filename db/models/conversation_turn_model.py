# stdlib
import uuid

# thirdparty
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.sql import func

# project
from db.db_setup import Base

TURN_ROLE_USER = "user"
TURN_ROLE_ASSISTANT = "assistant"
TURN_ROLE_SYSTEM = "system"

TURN_TYPE_DREAM_INTAKE = "dream_intake"
TURN_TYPE_DIALOGUE = "dialogue"
TURN_TYPE_CLARIFICATION = "clarification"
TURN_TYPE_SAFETY = "safety"


class ConversationTurn(Base):
    __tablename__ = "conversation_turns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(BigInteger, nullable=False, index=True, comment="Telegram user ID")
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dream_sessions.id"),
        nullable=False,
        index=True,
    )
    dream_id = Column(
        Integer,
        ForeignKey("dreams.id"),
        nullable=True,
        index=True,
    )
    role = Column(String, nullable=False, comment="user | assistant | system")
    turn_type = Column(String, nullable=False, comment="dream_intake | dialogue | clarification | safety")
    source = Column(String, nullable=False, default="telegram", server_default="telegram")
    text = Column(Text, nullable=False)
    metadata_json = Column(JSON, nullable=True, comment="DialogueTurnV1 fields except assistant_message text")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
