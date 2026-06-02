# stdlib
from dataclasses import dataclass, field

# project
from db.models.session_analysis_model import SessionAnalysis


class FakeRedis:
    """In-memory Redis subset for SET NX EX delivery lock tests."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def set(self, key: str, value: str, *, nx: bool = False, ex: int | None = None) -> bool | None:
        if nx and key in self._store:
            return None
        self._store[key] = value
        return True


@dataclass
class RecordingTelegramDelivery:
    calls: list[tuple[str, SessionAnalysis]] = field(default_factory=list)
    fail_on_call: int | None = None

    async def send_analysis(self, chat_id: str, analysis: SessionAnalysis) -> None:
        call_index = len(self.calls) + 1
        self.calls.append((chat_id, analysis))
        if self.fail_on_call is not None and call_index == self.fail_on_call:
            raise RuntimeError("telegram send failed")
