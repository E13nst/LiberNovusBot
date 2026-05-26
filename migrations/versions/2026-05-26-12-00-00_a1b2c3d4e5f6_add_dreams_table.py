"""add dreams table

Revision ID: a1b2c3d4e5f6
Revises: 6b5dae2e4e11
Create Date: 2026-05-26 12:00:00.000000

"""
# thirdparty
import sqlalchemy as sa
from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "6b5dae2e4e11"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dreams",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False, comment="Telegram user ID"),
        sa.Column("text", sa.Text(), nullable=False, comment="Dream text"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False, comment="Created At"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("dreams")
