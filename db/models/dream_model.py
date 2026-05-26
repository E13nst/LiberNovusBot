# thirdparty
from sqlalchemy import BigInteger, Column, DateTime, Integer, Text
from sqlalchemy.sql import func

# project
from db.db_setup import Base


class DreamModel(Base):
    __tablename__ = "dreams"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, comment="Telegram user ID")
    text = Column(Text, nullable=False, comment="Dream text")
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment="Created At")
