import uuid

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from db.db_setup import Base


class AdminPromptVersion(Base):
    __tablename__ = "admin_prompt_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prompt_type = Column(String, nullable=False, index=True, comment="Prompt family/type")
    version = Column(Integer, nullable=False, comment="Monotonic prompt version per prompt_type")
    content = Column(Text, nullable=False, comment="Prompt content managed through admin API")
    active_flag = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment="Created At")

    __table_args__ = (
        UniqueConstraint("prompt_type", "version", name="uq_admin_prompt_versions_type_version"),
        Index(
            "ix_admin_prompt_versions_one_active_per_type",
            "prompt_type",
            unique=True,
            postgresql_where=(active_flag.is_(True)),
        ),
    )
