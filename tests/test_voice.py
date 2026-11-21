"""Voice AI: best-effort TTS, text always available."""
from planner.voice import VOICE_LANGUAGES, briefing_script, speak


def test_voice_languages_offered():
    assert VOICE_LANGUAGES["English"] == "en"
    assert VOICE_LANGUAGES["Hindi"] == "hi"


def test_speak_empty_returns_none():
    assert speak("") is None
    assert speak("   ") is None


def test_briefing_script_english():
    briefing = {"headline": "AQI 269 (Poor) in Delhi",
                "weather": "18°C, humidity 79%",
                "timing": "Cleanest hour today: 3 PM."}
    script = briefing_script(briefing, "en")
    assert "269" in script
    assert "3 PM" in script


def test_briefing_script_hindi():
    briefing = {"headline": "AQI 269 (Poor) in Delhi",
                "weather": "18°C", "timing": ""}
    script = briefing_script(briefing, "hi")
    assert script.startswith("आज की हवा की जानकारी")
