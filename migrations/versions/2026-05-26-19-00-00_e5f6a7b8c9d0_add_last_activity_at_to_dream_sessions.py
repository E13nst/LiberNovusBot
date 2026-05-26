"""add last_activity_at to dream_sessions

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-26 19:00:00.000000

"""
# thirdparty
import sqlalchemy as sa
from alembic import op

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add column as nullable to avoid locking existing rows
    op.add_column(
        "dream_sessions",
        sa.Column("last_activity_at", sa.DateTime(), nullable=True),
    )

    # 2. Backfill: treat created_at as the last activity for existing sessions
    op.execute(
        sa.text(
            "UPDATE dream_sessions SET last_activity_at = created_at WHERE last_activity_at IS NULL"
        )
    )

    # 3. Enforce NOT NULL now that all rows have a value
    op.alter_column("dream_sessions", "last_activity_at", nullable=False)


def downgrade() -> None:
    op.drop_column("dream_sessions", "last_activity_at")
