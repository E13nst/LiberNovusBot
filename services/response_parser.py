import re
import json


class ResponseParseError(ValueError):
    """Raised when JSON object cannot be extracted from raw LLM response."""


_FENCED_JSON_PATTERN = re.compile(r"```(?:json)?\s*(?P<body>.*?)\s*```", flags=re.IGNORECASE | re.DOTALL)


def extract_json(raw: str) -> str:
    """Extract first JSON object string from raw text without normalization."""
    stripped = raw.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped

    for match in _FENCED_JSON_PATTERN.finditer(raw):
        candidate = match.group("body").strip()
        if candidate.startswith("{") and candidate.endswith("}"):
            return candidate

    decoder = json.JSONDecoder()
    for idx, char in enumerate(raw):
        if char != "{":
            continue
        try:
            _, end_idx = decoder.raw_decode(raw[idx:])
        except json.JSONDecodeError:
            continue
        return raw[idx : idx + end_idx]

    raise ResponseParseError("Could not extract JSON object from raw response")


def parse_json(raw_json: str) -> dict:
    """Strictly parse JSON string into dict."""
    try:
        value = json.loads(raw_json)
    except json.JSONDecodeError:
        raise ResponseParseError("Extracted payload is not valid JSON") from None
    if not isinstance(value, dict):
        raise ResponseParseError("Extracted JSON payload must be an object")
    return value
