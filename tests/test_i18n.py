"""Hindi + English UI strings."""
from planner.i18n import LANGUAGES, STRINGS, greeting, t


def test_languages_offered():
    assert "English" in LANGUAGES
    assert "हिंदी (Hindi)" in LANGUAGES


def test_every_key_has_english_and_hindi():
    for key, entry in STRINGS.items():
        assert entry.get("en"), key
        assert entry.get("hi"), key


def test_translate_known_keys():
    assert t("nav_home", "en") == "Home Dashboard"
    assert t("nav_home", "hi") == "होम डैशबोर्ड"
    assert t("why_this", "hi") == "यह क्यों?"


def test_translate_unknown_key_falls_back():
    assert t("no_such_key", "en") == "no_such_key"
    assert t("nav_home", "fr") == "Home Dashboard"


def test_greeting_by_hour():
    assert greeting(8, "en") == "Good morning"
    assert greeting(13, "en") == "Good afternoon"
    assert greeting(19, "en") == "Good evening"
    assert greeting(8, "hi") == "सुप्रभात"
