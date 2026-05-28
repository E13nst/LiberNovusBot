# stdlib
from datetime import datetime, timedelta, timezone

# project
from services.analysis_state_machine_types import SessionSnapshot, ThreadSnapshot
from services.session_service import INACTIVITY_THRESHOLD


def ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def is_session_closed(session: SessionSnapshot) -> bool:
    return session.status != "active"


def is_thread_closed(thread: ThreadSnapshot) -> bool:
    return thread.status == "closed"


def is_thread_idle(thread: ThreadSnapshot) -> bool:
    return thread.status == "idle"


def thread_activity_at(thread: ThreadSnapshot) -> datetime | None:
    if thread.last_activity_at is not None:
        return ensure_utc(thread.last_activity_at)
    if thread.created_at is not None:
        return ensure_utc(thread.created_at)
    return None


def is_thread_fresh(thread: ThreadSnapshot, now: datetime, threshold: timedelta = INACTIVITY_THRESHOLD) -> bool:
    activity = thread_activity_at(thread)
    if activity is None:
        return False
    return ensure_utc(now) - activity <= threshold
