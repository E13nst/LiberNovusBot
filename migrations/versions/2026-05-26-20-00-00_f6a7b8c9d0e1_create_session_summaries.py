"""create session summaries

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-05-26 20:00:00.000000

"""
# thirdparty
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "session_summaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False, comment="Dream session ID"),
        sa.Column("user_id", sa.BigInteger(), nullable=False, comment="Telegram user ID"),
        sa.Column("dream_count", sa.Integer(), nullable=False, comment="Number of dreams in session"),
        sa.Column("key_symbols", sa.JSON(), nullable=False, comment="Top rule-based symbols"),
        sa.Column("recurring_words", sa.JSON(), nullable=False, comment="Words appearing in multiple dreams"),
        sa.Column("raw_text_sample", sa.Text(), nullable=True, comment="Truncated sample of dream text"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False, comment="Created At"),
        sa.ForeignKeyConstraint(["session_id"], ["dream_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index("ix_session_summaries_user_id", "session_summaries", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_session_summaries_user_id", table_name="session_summaries")
    op.drop_table("session_summaries")
