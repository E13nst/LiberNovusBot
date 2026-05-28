"""create analysis jobs

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-05-28 15:00:00.000000

"""
# thirdparty
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "d0e1f2a3b4c5"
down_revision = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analysis_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False, comment="Dream session ID"),
        sa.Column(
            "thread_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Resolved analysis thread ID after successful execution",
        ),
        sa.Column(
            "status",
            sa.String(),
            nullable=False,
            comment="Job status: queued, running, completed, failed, cancelled",
        ),
        sa.Column("provider", sa.String(), nullable=False, comment="LLM provider identifier requested at enqueue time"),
        sa.Column("model", sa.String(), nullable=False, comment="Model identifier requested at enqueue time"),
        sa.Column("mode", sa.String(), server_default="auto", nullable=False, comment="Analysis mode request"),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False, comment="Execution attempt count"),
        sa.Column("max_attempts", sa.Integer(), server_default="1", nullable=False, comment="Maximum execution attempts"),
        sa.Column("last_error_class", sa.String(), nullable=True, comment="Last runtime/domain error class"),
        sa.Column("last_error_message", sa.Text(), nullable=True, comment="Last sanitized runtime/domain error message"),
        sa.Column("retryable", sa.Boolean(), server_default=sa.text("false"), nullable=False, comment="Last failure retryability"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False, comment="Created At"),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False, comment="Updated At"),
        sa.Column(
            "available_after",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Earliest acquisition time",
        ),
        sa.Column("started_at", sa.DateTime(), nullable=True, comment="First execution start timestamp"),
        sa.Column("completed_at", sa.DateTime(), nullable=True, comment="Terminal completion timestamp"),
        sa.Column("locked_by", sa.String(), nullable=True, comment="Runtime worker lock owner"),
        sa.Column("locked_at", sa.DateTime(), nullable=True, comment="Runtime worker lock timestamp"),
        sa.ForeignKeyConstraint(["session_id"], ["dream_sessions.id"], name="fk_analysis_jobs_session_id"),
        sa.ForeignKeyConstraint(["thread_id"], ["analysis_threads.id"], name="fk_analysis_jobs_thread_id"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analysis_jobs_session_id", "analysis_jobs", ["session_id"], unique=False)
    op.create_index("ix_analysis_jobs_thread_id", "analysis_jobs", ["thread_id"], unique=False)
    op.create_index("ix_analysis_jobs_status", "analysis_jobs", ["status"], unique=False)
    op.create_index(
        "ix_analysis_jobs_status_available_after_created_at",
        "analysis_jobs",
        ["status", "available_after", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_analysis_jobs_queued_available",
        "analysis_jobs",
        ["available_after", "created_at", "id"],
        unique=False,
        postgresql_where=sa.text("status = 'queued'"),
    )


def downgrade() -> None:
    op.drop_index("ix_analysis_jobs_queued_available", table_name="analysis_jobs")
    op.drop_index("ix_analysis_jobs_status_available_after_created_at", table_name="analysis_jobs")
    op.drop_index("ix_analysis_jobs_status", table_name="analysis_jobs")
    op.drop_index("ix_analysis_jobs_thread_id", table_name="analysis_jobs")
    op.drop_index("ix_analysis_jobs_session_id", table_name="analysis_jobs")
    op.drop_table("analysis_jobs")
