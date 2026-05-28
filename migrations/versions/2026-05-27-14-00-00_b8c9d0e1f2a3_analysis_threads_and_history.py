"""analysis threads and session analysis history

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-05-27 14:00:00.000000

"""
# thirdparty
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "b8c9d0e1f2a3"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analysis_threads",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False, comment="Dream session ID"),
        sa.Column("status", sa.String(), nullable=False, comment="Thread status: active, completed, superseded"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False, comment="Created At"),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False, comment="Updated At"),
        sa.Column("last_analysis_id", postgresql.UUID(as_uuid=True), nullable=True, comment="Most recent analysis"),
        sa.ForeignKeyConstraint(["session_id"], ["dream_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analysis_threads_session_id", "analysis_threads", ["session_id"], unique=False)
    op.create_index(
        "ix_analysis_threads_session_id_status",
        "analysis_threads",
        ["session_id", "status"],
        unique=False,
    )

    op.add_column(
        "session_analyses",
        sa.Column("thread_id", postgresql.UUID(as_uuid=True), nullable=True, comment="Analysis thread ID"),
    )
    op.add_column(
        "session_analyses",
        sa.Column(
            "is_latest",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
            comment="UI default flag within thread",
        ),
    )
    op.add_column(
        "session_analyses",
        sa.Column(
            "continuation_index",
            sa.Integer(),
            server_default="0",
            nullable=False,
            comment="Zero-based index within thread",
        ),
    )

    # Backfill: one thread per session, attach existing analyses, mark last as latest.
    op.execute(
        """
        INSERT INTO analysis_threads (id, session_id, status, created_at, updated_at)
        SELECT gen_random_uuid(), sa.session_id, 'active', MIN(sa.created_at), MAX(sa.created_at)
        FROM session_analyses sa
        GROUP BY sa.session_id
        """
    )
    op.execute(
        """
        UPDATE session_analyses sa
        SET thread_id = at.id
        FROM analysis_threads at
        WHERE at.session_id = sa.session_id
        """
    )
    op.execute(
        """
        UPDATE session_analyses sa
        SET is_latest = true
        FROM (
            SELECT DISTINCT ON (session_id) id
            FROM session_analyses
            ORDER BY session_id, created_at DESC, id DESC
        ) latest
        WHERE sa.id = latest.id
        """
    )
    op.execute(
        """
        UPDATE analysis_threads at
        SET last_analysis_id = sa.id
        FROM session_analyses sa
        WHERE sa.thread_id = at.id AND sa.is_latest = true
        """
    )

    op.drop_constraint("session_analyses_session_id_key", "session_analyses", type_="unique")
    op.alter_column("session_analyses", "thread_id", nullable=False)
    op.create_foreign_key(
        "fk_session_analyses_thread_id",
        "session_analyses",
        "analysis_threads",
        ["thread_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_analysis_threads_last_analysis",
        "analysis_threads",
        "session_analyses",
        ["last_analysis_id"],
        ["id"],
        use_alter=True,
    )
    op.create_index("ix_session_analyses_thread_id", "session_analyses", ["thread_id"], unique=False)
    op.create_index(
        "ix_session_analyses_one_latest_per_thread",
        "session_analyses",
        ["thread_id"],
        unique=True,
        postgresql_where=sa.text("is_latest = true"),
    )
    op.create_index(
        "ix_session_analyses_session_id_created_at",
        "session_analyses",
        ["session_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_session_analyses_session_id_created_at", table_name="session_analyses")
    op.drop_index("ix_session_analyses_one_latest_per_thread", table_name="session_analyses")
    op.drop_index("ix_session_analyses_thread_id", table_name="session_analyses")
    op.drop_constraint("fk_analysis_threads_last_analysis", "analysis_threads", type_="foreignkey")
    op.drop_constraint("fk_session_analyses_thread_id", "session_analyses", type_="foreignkey")
    op.drop_column("session_analyses", "continuation_index")
    op.drop_column("session_analyses", "is_latest")
    op.drop_column("session_analyses", "thread_id")
    op.drop_index("ix_analysis_threads_session_id_status", table_name="analysis_threads")
    op.drop_index("ix_analysis_threads_session_id", table_name="analysis_threads")
    op.drop_table("analysis_threads")
    op.create_unique_constraint("session_analyses_session_id_key", "session_analyses", ["session_id"])
