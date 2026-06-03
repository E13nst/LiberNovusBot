# stdlib
import re

_CRISIS_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bхочу\s+умереть\b", re.IGNORECASE),
    re.compile(r"\bпокончить\s+с\s+собой\b", re.IGNORECASE),
    re.compile(r"\bсамоубийств", re.IGNORECASE),
    re.compile(r"\bне\s+хочу\s+жить\b", re.IGNORECASE),
    re.compile(r"\bпорежу\s+себя\b", re.IGNORECASE),
    re.compile(r"\bсуицид", re.IGNORECASE),
    re.compile(r"\bself[-\s]?harm\b", re.IGNORECASE),
    re.compile(r"\bkill\s+myself\b", re.IGNORECASE),
)


def is_crisis_signal(text: str) -> bool:
    """Deterministic crisis/self-harm keyword detector (v1)."""
    normalized = " ".join(text.strip().lower().split())
    if not normalized:
        return False
    return any(pattern.search(normalized) for pattern in _CRISIS_PATTERNS)
