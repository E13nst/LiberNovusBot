"""add session_analyses analysis_job_id

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-06-01 18:00:00.000000

"""
# thirdparty
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "e1f2a3b4c5d6"
down_revision = "d0e1f2a3b4c5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "session_analyses",
        sa.Column(
            "analysis_job_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Runtime analysis job that produced this analysis; executor-owned trace link",
        ),
    )
    op.create_index(
        "ix_session_analyses_analysis_job_id",
        "session_analyses",
        ["analysis_job_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_session_analyses_analysis_job_id", table_name="session_analyses")
    op.drop_column("session_analyses", "analysis_job_id")
