"""Text and time helpers."""
import pytest

from planner.utils import clean_text, day_label, hour_label, safe_float


@pytest.mark.parametrize("iso,expected", [
    ("2026-11-21T00:00", "12 AM"),
    ("2026-11-21T01:00", "1 AM"),
    ("2026-11-21T11:00", "11 AM"),
    ("2026-11-21T12:00", "12 PM"),
    ("2026-11-21T13:00", "1 PM"),
    ("2026-11-21T15:00", "3 PM"),
    ("2026-11-21T23:00", "11 PM"),
])
def test_hour_label(iso, expected):
    assert hour_label(iso) == expected


def test_hour_label_bad_input_passthrough():
    assert hour_label("not-a-time") == "not-a-time"


def test_day_label():
    assert day_label("2026-11-21T14:00") == "Sat 21 Nov"
    assert day_label("2026-11-29T00:00") == "Sun 29 Nov"


def test_day_label_bad_input_passthrough():
    assert day_label("nope") == "nope"


def test_clean_text_collapses_and_trims():
    assert clean_text("  hello   world \n ") == "hello world"
    assert clean_text(None) == ""
    assert clean_text("") == ""


def test_clean_text_caps_length():
    assert clean_text("abcdef", 3) == "abc"


@pytest.mark.parametrize("value,expected", [
    ("12.5", 12.5), (7, 7.0), (None, None), ("abc", None),
])
def test_safe_float(value, expected):
    assert safe_float(value) == expected


def test_safe_float_custom_default():
    assert safe_float("abc", default=1.5) == 1.5
