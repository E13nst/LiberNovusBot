"""backfill dream sessions

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-26 14:01:00.000000

"""
# stdlib
import uuid

# thirdparty
from alembic import op
from sqlalchemy import text

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    user_ids = connection.execute(text("SELECT DISTINCT user_id FROM dreams")).scalars().all()

    for user_id in user_ids:
        session_id = uuid.uuid4()
        connection.execute(
            text(
                """
                INSERT INTO dream_sessions (id, user_id, status, created_at, updated_at)
                VALUES (:id, :user_id, 'active', now(), now())
                """
            ),
            {"id": session_id, "user_id": user_id},
        )
        connection.execute(
            text(
                """
                UPDATE dreams SET session_id = :session_id WHERE user_id = :user_id
                """
            ),
            {"session_id": session_id, "user_id": user_id},
        )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(text("UPDATE dreams SET session_id = NULL"))
    connection.execute(text("DELETE FROM dream_sessions"))
