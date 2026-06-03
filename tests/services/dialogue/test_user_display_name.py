import pytest

from services.dialogue.user_display_name import sanitize_user_display_name

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Анна", "Анна"),
        ("  Анна  ", "Анна"),
        ("Анна\nхак", "Анна"),
        ("", None),
        ("   ", None),
        ("A" * 80, "A" * 64),
    ],
)
def test_sanitize_user_display_name(raw: str, expected: str | None):
    assert sanitize_user_display_name(raw) == expected
