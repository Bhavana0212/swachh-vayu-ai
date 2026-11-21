"""Urban Air Quality Assistant — planning and air-quality logic.

Pure-Python modules with no Streamlit dependency, so they can be tested
without a running app. Live data comes from the Open-Meteo Air Quality API
(Copernicus CAMS modelled data); see planner/api.py.
"""

__all__ = [
    "aqi",
    "api",
    "routine",
    "indoor",
    "alternatives",
    "ai",
    "export",
    "utils",
    "why",
    "safety",
    "whatif",
    "score",
    "household",
    "habits",
    "alerts",
]
