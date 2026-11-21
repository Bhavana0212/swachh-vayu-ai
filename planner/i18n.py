"""Hindi + English UI strings.

The UI toggle switches the main navigation and headings between English
and Hindi. Longer educational content stays in English with Hindi
summaries where noted; regional languages beyond Hindi are available
best-effort through the AI chat only (no fake full-UI translation).
"""
from __future__ import annotations

LANGUAGES = {"English": "en", "हिंदी (Hindi)": "hi"}

STRINGS: dict[str, dict[str, str]] = {
    "app_name": {"en": "SwachhVayu AI", "hi": "स्वच्छवायु AI"},
    "tagline": {
        "en": "Don't just check the air. Know what to do, when to do it, "
              "and why it matters.",
        "hi": "सिर्फ़ हवा मत देखिए — जानिए क्या करना है, कब करना है, "
              "और क्यों ज़रूरी है।",
    },
    "nav_home": {"en": "Home Dashboard", "hi": "होम डैशबोर्ड"},
    "nav_locations": {"en": "My Locations", "hi": "मेरे स्थान"},
    "nav_forecast": {"en": "Forecast & Predictor", "hi": "पूर्वानुमान"},
    "nav_routine": {"en": "My Routine", "hi": "मेरी दिनचर्या"},
    "nav_activity": {"en": "Activity Planner", "hi": "गतिविधि योजना"},
    "nav_indoor": {"en": "Indoor Air", "hi": "घर की हवा"},
    "nav_alternatives": {"en": "Alternatives & Impact", "hi": "विकल्प और प्रभाव"},
    "nav_whatif": {"en": "What If Simulator", "hi": "क्या होगा अगर..."},
    "nav_ai": {"en": "AI Assistant", "hi": "AI सहायक"},
    "nav_compare": {"en": "Compare & Map", "hi": "तुलना और मानचित्र"},
    "nav_alerts": {"en": "Alerts", "hi": "अलर्ट"},
    "nav_family": {"en": "Family & Household", "hi": "परिवार"},
    "nav_equipment": {"en": "Mask & Purifier Guide", "hi": "मास्क और प्यूरीफायर"},
    "nav_awareness": {"en": "Awareness", "hi": "जागरूकता"},
    "nav_community": {"en": "Community", "hi": "समुदाय"},
    "nav_analytics": {"en": "Analytics", "hi": "विश्लेषण"},
    "nav_plan": {"en": "My Plan & Reports", "hi": "मेरी योजना और रिपोर्ट"},
    "nav_learn": {"en": "Learn & Digital Twin", "hi": "सीखें और डिजिटल ट्विन"},
    "city": {"en": "City", "hi": "शहर"},
    "language": {"en": "Language / भाषा", "hi": "भाषा / Language"},
    "indian_aqi": {"en": "Calculated Indian AQI", "hi": "भारतीय वायु गुणवत्ता सूचकांक"},
    "why_this": {"en": "Why this?", "hi": "यह क्यों?"},
    "why_now": {"en": "Why now?", "hi": "अभी क्यों?"},
    "what_impact": {"en": "What impact?", "hi": "क्या असर होगा?"},
    "good_morning": {"en": "Good morning", "hi": "सुप्रभात"},
    "good_afternoon": {"en": "Good afternoon", "hi": "नमस्कार"},
    "good_evening": {"en": "Good evening", "hi": "शुभ संध्या"},
    "sample_banner": {
        "en": "Sample data — live data unavailable. The numbers below are "
              "typical values, not measurements.",
        "hi": "नमूना डेटा — लाइव डेटा उपलब्ध नहीं है। नीचे दिए गए आंकड़े "
              "सामान्य मान हैं, माप नहीं।",
    },
    "india_only": {
        "en": "SwachhVayu AI covers India only.",
        "hi": "स्वच्छवायु AI केवल भारत के लिए है।",
    },
    "health_disclaimer": {
        "en": "General information, not medical advice. If you have "
              "breathing difficulty, seek medical care promptly.",
        "hi": "यह सामान्य जानकारी है, चिकित्सा सलाह नहीं। सांस लेने में "
              "तकलीफ़ हो तो तुरंत डॉक्टर से संपर्क करें।",
    },
}


def t(key: str, lang: str = "en") -> str:
    """Translate a UI key; falls back to English, then the key itself."""
    entry = STRINGS.get(key)
    if not entry:
        return key
    return entry.get(lang) or entry.get("en") or key


def greeting(hour: int, lang: str = "en") -> str:
    """Time-of-day greeting."""
    if hour < 12:
        return t("good_morning", lang)
    if hour < 17:
        return t("good_afternoon", lang)
    return t("good_evening", lang)
