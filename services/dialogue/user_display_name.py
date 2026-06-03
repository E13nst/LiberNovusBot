# stdlib
import re

_MAX_DISPLAY_NAME_LEN = 64
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def sanitize_user_display_name(raw: str | None) -> str | None:
    if raw is None:
        return None
    first_line = raw.split("\n", 1)[0].split("\r", 1)[0]
    cleaned = _CONTROL_CHARS.sub(" ", first_line)
    cleaned = " ".join(cleaned.split()).strip()
    if not cleaned:
        return None
    return cleaned[:_MAX_DISPLAY_NAME_LEN]

