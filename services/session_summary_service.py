# stdlib
import re
import uuid
from collections import Counter
from uuid import UUID

# thirdparty
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

# project
from db.models.dream_model import Dream
from db.models.session_model import DreamSession
from db.models.session_summary_model import SessionSummary

_MAX_KEY_SYMBOLS = 10
_RAW_TEXT_DREAM_LIMIT = 5
_RAW_TEXT_CHAR_LIMIT = 1000
_TOKEN_PATTERN = re.compile(r"\b[а-яёa-z]+\b", re.IGNORECASE)

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "but",
        "by",
        "for",
        "from",
        "had",
        "has",
        "have",
        "he",
        "her",
        "his",
        "i",
        "in",
        "is",
        "it",
        "my",
        "of",
        "on",
        "or",
        "she",
        "that",
        "the",
        "to",
        "was",
        "were",
        "with",
        "you",
        "а",
        "в",
        "во",
        "и",
        "к",
        "как",
        "ко",
        "мне",
        "мой",
        "на",
        "не",
        "но",
        "о",
        "он",
        "она",
        "от",
        "по",
        "с",
        "со",
        "то",
        "у",
        "что",
        "я",
    }
)


def _tokenize(text: str) -> list[str]:
    return [
        token.lower()
        for token in _TOKEN_PATTERN.findall(text)
        if token.lower() not in _STOPWORDS
    ]


def _rank_words(counter: Counter[str]) -> list[str]:
    return [
        word
        for word, _count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    ]


async def build_session_summary(db: AsyncSession, session_id: UUID) -> SessionSummary:
    session = await db.scalar(select(DreamSession).where(DreamSession.id == session_id))
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    result = await db.execute(
        select(Dream)
        .where(Dream.session_id == session_id)
        .order_by(Dream.created_at.asc(), Dream.id.asc())
    )
    dreams = list(result.scalars().all())

    all_tokens: list[str] = []
    per_dream_tokens: Counter[str] = Counter()
    for dream in dreams:
        tokens = _tokenize(dream.text)
        all_tokens.extend(tokens)
        per_dream_tokens.update(set(tokens))

    word_counts = Counter(all_tokens)
    raw_text_sample = " ".join(dream.text for dream in dreams[:_RAW_TEXT_DREAM_LIMIT])
    raw_text_sample = raw_text_sample[:_RAW_TEXT_CHAR_LIMIT] if raw_text_sample else None

    return SessionSummary(
        id=uuid.uuid4(),
        session_id=session.id,
        user_id=session.user_id,
        dream_count=len(dreams),
        key_symbols=_rank_words(word_counts)[:_MAX_KEY_SYMBOLS],
        recurring_words=_rank_words(
            Counter({word: word_counts[word] for word, count in per_dream_tokens.items() if count > 1})
        ),
        raw_text_sample=raw_text_sample,
    )


async def save_session_summary(db: AsyncSession, summary: SessionSummary) -> SessionSummary:
    stmt = (
        insert(SessionSummary)
        .values(
            id=summary.id or uuid.uuid4(),
            session_id=summary.session_id,
            user_id=summary.user_id,
            dream_count=summary.dream_count,
            key_symbols=summary.key_symbols,
            recurring_words=summary.recurring_words,
            raw_text_sample=summary.raw_text_sample,
        )
        .on_conflict_do_update(
            index_elements=["session_id"],
            set_={
                "user_id": summary.user_id,
                "dream_count": summary.dream_count,
                "key_symbols": summary.key_symbols,
                "recurring_words": summary.recurring_words,
                "raw_text_sample": summary.raw_text_sample,
            },
        )
    )
    await db.execute(stmt)
    await db.flush()

    saved = await get_session_summary(db, summary.session_id)
    if saved is None:
        raise RuntimeError("Failed to save session summary")
    return saved


async def get_session_summary(db: AsyncSession, session_id: UUID) -> SessionSummary | None:
    query = (
        select(SessionSummary)
        .where(SessionSummary.session_id == session_id)
        .execution_options(populate_existing=True)
    )
    return await db.scalar(query)
