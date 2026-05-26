"""enforce dream session not null

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-26 14:02:00.000000

"""
# thirdparty
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    null_count = connection.execute(
        sa.text("SELECT COUNT(*) FROM dreams WHERE session_id IS NULL")
    ).scalar_one()
    if null_count > 0:
        raise RuntimeError(
            f"Cannot enforce NOT NULL on dreams.session_id: {null_count} rows still have NULL. "
            "Run backfill migration c3d4e5f6a7b8 first."
        )

    op.alter_column(
        "dreams",
        "session_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "dreams",
        "session_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
