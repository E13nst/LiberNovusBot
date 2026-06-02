"""admin console mvp

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-06-02 18:30:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f2a3b4c5d6e7"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_prompt_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prompt_type", sa.String(), nullable=False, comment="Prompt family/type"),
        sa.Column("version", sa.Integer(), nullable=False, comment="Monotonic prompt version per prompt_type"),
        sa.Column("content", sa.Text(), nullable=False, comment="Prompt content managed through admin API"),
        sa.Column("active_flag", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False, comment="Created At"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("prompt_type", "version", name="uq_admin_prompt_versions_type_version"),
    )
    op.create_index("ix_admin_prompt_versions_prompt_type", "admin_prompt_versions", ["prompt_type"])
    op.create_index(
        "ix_admin_prompt_versions_one_active_per_type",
        "admin_prompt_versions",
        ["prompt_type"],
        unique=True,
        postgresql_where=sa.text("active_flag IS TRUE"),
    )

    op.create_table(
        "dialogue_policy_traces",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False, comment="Telegram user ID"),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Resolved session for stateful reflection routes",
        ),
        sa.Column("dream_id", sa.Integer(), nullable=True, comment="Dream row created by reflection route, if any"),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Analysis job enqueued by reflection route, if any",
        ),
        sa.Column("input_json", sa.JSON(), nullable=False, comment="PolicyInput projection without raw text"),
        sa.Column("decision_json", sa.JSON(), nullable=False, comment="PolicyDecision projection"),
        sa.Column("route", sa.String(), nullable=False),
        sa.Column("reason_code", sa.String(), nullable=False),
        sa.Column("outcome_json", sa.JSON(), nullable=False, comment="Execution outcome projection"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False, comment="Created At"),
        sa.ForeignKeyConstraint(["dream_id"], ["dreams.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["analysis_jobs.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["dream_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dialogue_policy_traces_user_id", "dialogue_policy_traces", ["user_id"])
    op.create_index("ix_dialogue_policy_traces_session_id", "dialogue_policy_traces", ["session_id"])
    op.create_index("ix_dialogue_policy_traces_dream_id", "dialogue_policy_traces", ["dream_id"])
    op.create_index("ix_dialogue_policy_traces_job_id", "dialogue_policy_traces", ["job_id"])
    op.create_index("ix_dialogue_policy_traces_route", "dialogue_policy_traces", ["route"])


def downgrade() -> None:
    op.drop_index("ix_dialogue_policy_traces_route", table_name="dialogue_policy_traces")
    op.drop_index("ix_dialogue_policy_traces_job_id", table_name="dialogue_policy_traces")
    op.drop_index("ix_dialogue_policy_traces_dream_id", table_name="dialogue_policy_traces")
    op.drop_index("ix_dialogue_policy_traces_session_id", table_name="dialogue_policy_traces")
    op.drop_index("ix_dialogue_policy_traces_user_id", table_name="dialogue_policy_traces")
    op.drop_table("dialogue_policy_traces")
    op.drop_index("ix_admin_prompt_versions_one_active_per_type", table_name="admin_prompt_versions")
    op.drop_index("ix_admin_prompt_versions_prompt_type", table_name="admin_prompt_versions")
    op.drop_table("admin_prompt_versions")
