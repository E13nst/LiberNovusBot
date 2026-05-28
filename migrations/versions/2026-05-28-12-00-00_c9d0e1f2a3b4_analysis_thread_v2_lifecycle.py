"""analysis thread v2 lifecycle: idle/closed, last_activity_at, one active per session

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-05-28 12:00:00.000000

"""
# thirdparty
import sqlalchemy as sa
from alembic import op

revision = "c9d0e1f2a3b4"
down_revision = "b8c9d0e1f2a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "analysis_threads",
        sa.Column(
            "last_activity_at",
            sa.DateTime(),
            nullable=True,
            comment="Updated only when analysis is persisted for this thread",
        ),
    )

    op.execute(
        """
        UPDATE analysis_threads at
        SET last_activity_at = COALESCE(sa.created_at, at.updated_at, at.created_at)
        FROM session_analyses sa
        WHERE sa.thread_id = at.id AND sa.is_latest = true
        """
    )
    op.execute(
        """
        UPDATE analysis_threads
        SET last_activity_at = COALESCE(updated_at, created_at)
        WHERE last_activity_at IS NULL
        """
    )

    op.execute(
        """
        UPDATE analysis_threads
        SET status = 'idle'
        WHERE status = 'superseded'
        """
    )
    op.execute(
        """
        UPDATE analysis_threads
        SET status = 'closed'
        WHERE status = 'completed'
        """
    )

    op.create_index(
        "ix_analysis_threads_one_active_per_session",
        "analysis_threads",
        ["session_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index("ix_analysis_threads_one_active_per_session", table_name="analysis_threads")
    op.execute(
        """
        UPDATE analysis_threads
        SET status = 'superseded'
        WHERE status = 'idle'
        """
    )
    op.execute(
        """
        UPDATE analysis_threads
        SET status = 'completed'
        WHERE status = 'closed'
        """
    )
    op.drop_column("analysis_threads", "last_activity_at")
