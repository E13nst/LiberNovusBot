# thirdparty
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

# project
from db.db_setup import get_session
from db.schemas.journal_schema import JournalDreamDetail, JournalDreamListItem, JournalPatternSummary, JournalSessionListItem
from services.journal.journal_service import (
    get_journal_dream_detail,
    get_journal_patterns,
    list_journal_dreams,
    list_journal_sessions,
)
from utils.journal_auth import require_journal_user_id

journal_router = APIRouter(prefix="/journal", tags=["Journal"])


@journal_router.get("/sessions", response_model=list[JournalSessionListItem])
async def journal_list_sessions(
    user_id: int = Depends(require_journal_user_id),
    db: AsyncSession = Depends(get_session),
):
    return await list_journal_sessions(db, user_id)


@journal_router.get("/dreams", response_model=list[JournalDreamListItem])
async def journal_list_dreams(
    user_id: int = Depends(require_journal_user_id),
    db: AsyncSession = Depends(get_session),
):
    return await list_journal_dreams(db, user_id)


@journal_router.get("/dreams/{dream_id}", response_model=JournalDreamDetail)
async def journal_get_dream(
    dream_id: int,
    user_id: int = Depends(require_journal_user_id),
    db: AsyncSession = Depends(get_session),
):
    detail = await get_journal_dream_detail(db, user_id, dream_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Dream not found")
    return detail


@journal_router.get("/patterns", response_model=JournalPatternSummary)
async def journal_patterns(
    user_id: int = Depends(require_journal_user_id),
    db: AsyncSession = Depends(get_session),
):
    return await get_journal_patterns(db, user_id)
