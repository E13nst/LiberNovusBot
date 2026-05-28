"""create session analyses

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-05-27 12:00:00.000000

"""
# thirdparty
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "a7b8c9d0e1f2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "session_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False, comment="Dream session ID"),
        sa.Column("user_id", sa.BigInteger(), nullable=False, comment="Telegram user ID"),
        sa.Column("provider", sa.String(), nullable=False, comment="LLM provider identifier, e.g. mock"),
        sa.Column("model", sa.String(), nullable=False, comment="Model identifier, e.g. mock-v1"),
        sa.Column("prompt_version", sa.String(), nullable=False, comment="Prompt contract version used"),
        sa.Column("analysis_version", sa.String(), nullable=False, comment="Analysis output schema version"),
        sa.Column("analysis_json", sa.JSON(), nullable=False, comment="Validated structured analysis output"),
        sa.Column("raw_response", sa.Text(), nullable=True, comment="Optional raw provider response"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False, comment="Created At"),
        sa.ForeignKeyConstraint(["session_id"], ["dream_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index("ix_session_analyses_user_id", "session_analyses", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_session_analyses_user_id", table_name="session_analyses")
    op.drop_table("session_analyses")
