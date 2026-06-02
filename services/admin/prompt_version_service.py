from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.admin_prompt_version_model import AdminPromptVersion


async def list_prompt_versions(db: AsyncSession) -> list[AdminPromptVersion]:
    result = await db.execute(
        select(AdminPromptVersion).order_by(
            AdminPromptVersion.prompt_type.asc(),
            AdminPromptVersion.version.desc(),
            AdminPromptVersion.created_at.desc(),
        )
    )
    return list(result.scalars().all())


async def get_prompt_version(db: AsyncSession, prompt_id: UUID) -> AdminPromptVersion | None:
    return await db.scalar(select(AdminPromptVersion).where(AdminPromptVersion.id == prompt_id))


async def create_prompt_version(
    db: AsyncSession,
    *,
    prompt_type: str,
    content: str,
    active: bool = True,
) -> AdminPromptVersion:
    latest_version = await db.scalar(
        select(func.max(AdminPromptVersion.version)).where(AdminPromptVersion.prompt_type == prompt_type)
    )
    next_version = int(latest_version or 0) + 1

    if active:
        await db.execute(
            update(AdminPromptVersion)
            .where(AdminPromptVersion.prompt_type == prompt_type)
            .values(active_flag=False)
        )

    row = AdminPromptVersion(
        prompt_type=prompt_type,
        version=next_version,
        content=content,
        active_flag=active,
    )
    db.add(row)
    await db.flush()
    return row


async def create_next_prompt_version(
    db: AsyncSession,
    *,
    previous_id: UUID,
    content: str,
) -> AdminPromptVersion | None:
    previous = await get_prompt_version(db, previous_id)
    if previous is None:
        return None
    return await create_prompt_version(
        db,
        prompt_type=previous.prompt_type,
        content=content,
        active=True,
    )
