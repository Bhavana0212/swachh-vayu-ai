"""Voice AI (best-effort): spoken AQI explanations via gTTS.

gTTS is free but needs internet at runtime. Every voice feature keeps the
full text visible, so the app works with or without audio. If gTTS is not
installed or the request fails, speak() returns None and the UI shows the
text only.
"""
from __future__ import annotations

import io

VOICE_LANGUAGES = {
    "English": "en",
    "Hindi": "hi",
    "Hinglish (Hindi, Roman script)": "hi",
}


def speak(text: str, lang: str = "en") -> bytes | None:
    """Synthesise speech as MP3 bytes, or None when unavailable.

    `text` is capped at 2,000 characters (gTTS handles long text poorly).
    """
    text = (text or "").strip()
    if not text:
        return None
    text = text[:2000]
    try:
        from gtts import gTTS
    except ImportError:
        return None
    try:
        buffer = io.BytesIO()
        gTTS(text=text, lang=lang, slow=False).write_to_fp(buffer)
        data = buffer.getvalue()
        return data if data else None
    except Exception:
        return None


def briefing_script(briefing: dict[str, str], lang: str = "en") -> str:
    """Turn a morning-briefing dict into a short spoken script."""
    if lang == "hi":
        return ("आज की हवा की जानकारी। " + briefing.get("headline", "") +
                " मौसम: " + briefing.get("weather", "") + " " +
                briefing.get("timing", ""))
    return ("Today's air briefing. " + briefing.get("headline", "") +
            " Weather: " + briefing.get("weather", "") + " " +
            briefing.get("timing", ""))
