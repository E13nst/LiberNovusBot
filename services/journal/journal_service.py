# stdlib
from uuid import UUID

# thirdparty
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

# project
from db.models.conversation_turn_model import ConversationTurn
from db.models.dream_memory_model import DreamMemory
from db.models.dream_model import Dream
from db.models.session_model import DreamSession
from db.models.session_summary_model import SessionSummary
from db.schemas.journal_schema import (
    JournalDreamDetail,
    JournalDreamListItem,
    JournalPatternSummary,
    JournalSessionListItem,
)


async def list_journal_sessions(db: AsyncSession, user_id: int) -> list[JournalSessionListItem]:
    rows = await db.execute(
        select(DreamSession).where(DreamSession.user_id == user_id).order_by(DreamSession.created_at.desc())
    )
    sessions = list(rows.scalars().all())
    items: list[JournalSessionListItem] = []
    for session in sessions:
        dream_count = await db.scalar(
            select(func.count()).select_from(Dream).where(Dream.session_id == session.id)
        )
        items.append(
            JournalSessionListItem(
                id=session.id,
                status=session.status,
                created_at=session.created_at,
                last_activity_at=session.last_activity_at,
                dream_count=int(dream_count or 0),
            )
        )
    return items


async def list_journal_dreams(db: AsyncSession, user_id: int) -> list[JournalDreamListItem]:
    rows = await db.execute(
        select(Dream).where(Dream.user_id == user_id).order_by(Dream.created_at.desc(), Dream.id.desc())
    )
    dreams = list(rows.scalars().all())
    items: list[JournalDreamListItem] = []
    for dream in dreams:
        memory = await db.scalar(select(DreamMemory).where(DreamMemory.dream_id == dream.id))
        items.append(
            JournalDreamListItem(
                id=dream.id,
                session_id=dream.session_id,
                created_at=dream.created_at,
                excerpt=dream.text[:200],
                has_memory=memory is not None,
            )
        )
    return items


async def get_journal_dream_detail(db: AsyncSession, user_id: int, dream_id: int) -> JournalDreamDetail | None:
    dream = await db.scalar(select(Dream).where(Dream.id == dream_id, Dream.user_id == user_id))
    if dream is None:
        return None

    memory = await db.scalar(select(DreamMemory).where(DreamMemory.dream_id == dream_id))
    turns_result = await db.execute(
        select(ConversationTurn)
        .where(ConversationTurn.dream_id == dream_id)
        .order_by(ConversationTurn.created_at.asc())
    )
    turns = list(turns_result.scalars().all())

    return JournalDreamDetail(
        id=dream.id,
        session_id=dream.session_id,
        text=dream.text,
        created_at=dream.created_at,
        memory_json=memory.memory_json if memory else None,
        dialogue_turns=[
            {"role": turn.role, "text": turn.text, "turn_type": turn.turn_type, "created_at": turn.created_at.isoformat()}
            for turn in turns
        ],
    )


async def get_journal_patterns(db: AsyncSession, user_id: int) -> JournalPatternSummary:
    summaries = await db.execute(select(SessionSummary).where(SessionSummary.user_id == user_id))
    symbol_counts: dict[str, int] = {}
    word_counts: dict[str, int] = {}
    for summary in summaries.scalars().all():
        for symbol in summary.key_symbols or []:
            symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
        for word in summary.recurring_words or []:
            word_counts[word] = word_counts.get(word, 0) + 1

    top_symbols = sorted(symbol_counts.items(), key=lambda item: (-item[1], item[0]))[:20]
    top_words = sorted(word_counts.items(), key=lambda item: (-item[1], item[0]))[:20]
    return JournalPatternSummary(
        recurring_symbols=[{"symbol": name, "count": count} for name, count in top_symbols],
        recurring_words=[{"word": name, "count": count} for name, count in top_words],
    )
