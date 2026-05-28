# thirdparty
import pytest

# project
from services.response_parser import ResponseParseError, extract_json, parse_json


def test_extract_json_handles_plain_json():
    parsed = parse_json(extract_json('{"ok": true, "value": 1}'))
    assert parsed["ok"] is True
    assert parsed["value"] == 1


def test_extract_json_handles_code_fence():
    raw = "some preface\n```json\n{\"themes\": [\"a\"]}\n```\ntrailer"
    parsed = parse_json(extract_json(raw))
    assert parsed["themes"] == ["a"]


def test_extract_json_raises_when_missing_json():
    with pytest.raises(ResponseParseError):
        extract_json("no json body here")


def test_parse_json_rejects_non_object():
    with pytest.raises(ResponseParseError):
        parse_json("[1, 2, 3]")
