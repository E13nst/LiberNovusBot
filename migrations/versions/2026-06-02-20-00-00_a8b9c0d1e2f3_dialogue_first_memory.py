"""dialogue_first_memory: conversation_turns, dream_memories, dream_id on jobs

Revision ID: a8b9c0d1e2f3
Revises: f2a3b4c5d6e7
Create Date: 2026-06-02 20:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a8b9c0d1e2f3"
down_revision: Union[str, None] = "f2a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversation_turns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dream_sessions.id"), nullable=False),
        sa.Column("dream_id", sa.Integer(), sa.ForeignKey("dreams.id"), nullable=True),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("turn_type", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False, server_default="telegram"),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("metadata_json", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_conversation_turns_user_id", "conversation_turns", ["user_id"])
    op.create_index("ix_conversation_turns_session_id", "conversation_turns", ["session_id"])
    op.create_index("ix_conversation_turns_dream_id", "conversation_turns", ["dream_id"])

    op.create_table(
        "dream_memories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("dream_id", sa.Integer(), sa.ForeignKey("dreams.id"), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dream_sessions.id"), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("memory_version", sa.String(), nullable=False),
        sa.Column("memory_json", postgresql.JSON(), nullable=False),
        sa.Column("analysis_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_dream_memories_dream_id", "dream_memories", ["dream_id"], unique=True)
    op.create_index("ix_dream_memories_session_id", "dream_memories", ["session_id"])
    op.create_index("ix_dream_memories_user_id", "dream_memories", ["user_id"])

    op.add_column("analysis_jobs", sa.Column("dream_id", sa.Integer(), sa.ForeignKey("dreams.id"), nullable=True))
    op.create_index("ix_analysis_jobs_dream_id", "analysis_jobs", ["dream_id"])


def downgrade() -> None:
    op.drop_index("ix_analysis_jobs_dream_id", table_name="analysis_jobs")
    op.drop_column("analysis_jobs", "dream_id")
    op.drop_table("dream_memories")
    op.drop_table("conversation_turns")
