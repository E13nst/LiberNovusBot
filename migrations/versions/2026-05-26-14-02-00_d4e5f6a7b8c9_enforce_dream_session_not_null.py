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
        connection.execute(
            sa.text(
                """
                WITH orphan_users AS (
                    SELECT DISTINCT user_id
                    FROM dreams
                    WHERE session_id IS NULL
                ),
                existing_active AS (
                    SELECT DISTINCT ON (user_id) user_id, id
                    FROM dream_sessions
                    WHERE status = 'active'
                      AND user_id IN (SELECT user_id FROM orphan_users)
                    ORDER BY user_id, updated_at DESC
                ),
                users_to_create AS (
                    SELECT ou.user_id
                    FROM orphan_users ou
                    LEFT JOIN existing_active ea ON ea.user_id = ou.user_id
                    WHERE ea.id IS NULL
                )
                INSERT INTO dream_sessions (id, user_id, status, created_at, updated_at)
                SELECT
                    (
                        substr(md5('orphan:' || utc.user_id::text), 1, 8) || '-' ||
                        substr(md5('orphan:' || utc.user_id::text), 9, 4) || '-' ||
                        substr(md5('orphan:' || utc.user_id::text), 13, 4) || '-' ||
                        substr(md5('orphan:' || utc.user_id::text), 17, 4) || '-' ||
                        substr(md5('orphan:' || utc.user_id::text), 21, 12)
                    )::uuid,
                    utc.user_id,
                    'active',
                    now(),
                    now()
                FROM users_to_create utc
                ON CONFLICT (id) DO NOTHING
                """
            )
        )
        connection.execute(
            sa.text(
                """
                WITH orphan_users AS (
                    SELECT DISTINCT user_id
                    FROM dreams
                    WHERE session_id IS NULL
                ),
                target_sessions AS (
                    SELECT
                        ou.user_id,
                        COALESCE(
                            (
                                SELECT ds.id
                                FROM dream_sessions ds
                                WHERE ds.user_id = ou.user_id
                                  AND ds.status = 'active'
                                ORDER BY ds.updated_at DESC
                                LIMIT 1
                            ),
                            (
                                (
                                    substr(md5('orphan:' || ou.user_id::text), 1, 8) || '-' ||
                                    substr(md5('orphan:' || ou.user_id::text), 9, 4) || '-' ||
                                    substr(md5('orphan:' || ou.user_id::text), 13, 4) || '-' ||
                                    substr(md5('orphan:' || ou.user_id::text), 17, 4) || '-' ||
                                    substr(md5('orphan:' || ou.user_id::text), 21, 12)
                                )::uuid
                            )
                        ) AS session_id
                    FROM orphan_users ou
                )
                UPDATE dreams d
                SET session_id = ts.session_id
                FROM target_sessions ts
                WHERE d.user_id = ts.user_id
                  AND d.session_id IS NULL
                """
            )
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
