"""add dream sessions table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-26 14:00:00.000000

"""
# thirdparty
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dream_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False, comment="Telegram user ID"),
        sa.Column("status", sa.String(), nullable=False, comment="Session status: active, paused, closed"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False, comment="Created At"),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False, comment="Updated At"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dream_sessions_user_id", "dream_sessions", ["user_id"], unique=False)

    op.add_column(
        "dreams",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True, comment="Dream session ID"),
    )
    op.create_foreign_key(
        "fk_dreams_session_id_dream_sessions",
        "dreams",
        "dream_sessions",
        ["session_id"],
        ["id"],
    )
    op.create_index("ix_dreams_session_id", "dreams", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_dreams_session_id", table_name="dreams")
    op.drop_constraint("fk_dreams_session_id_dream_sessions", "dreams", type_="foreignkey")
    op.drop_column("dreams", "session_id")
    op.drop_index("ix_dream_sessions_user_id", table_name="dream_sessions")
    op.drop_table("dream_sessions")
