"""School Air Safety Planner: outdoor-activity guidance for schools,
children's sports timing, a parent-friendly summary and a school
awareness checklist. Conservative and non-diagnostic.
"""
from __future__ import annotations

from dataclasses import dataclass

from .api import AirReport
from .utils import hour_label

SCHOOL_CHECKLIST = [
    "Check the morning AQI before assembly and outdoor periods.",
    "Move PT and sports to the cleanest hour of the day when the AQI is "
    "above 100 (Indian AQI).",
    "Keep classroom windows closed on Poor or worse days; use purifiers "
    "where available.",
    "Keep N95/FFP2 masks available for children who commute on foot or "
    "by cycle.",
    "Share the day's AQI with parents on the school group each morning.",
    "Teach children the AQI colours and what they mean (see the "
    "Community page quiz).",
    "Avoid outdoor events on Severe days; move them indoors or postpone.",
    "Plant and maintain trees on the school campus for shade and dust "
    "control.",
]


@dataclass
class SchoolPlan:
    """Today's school guidance."""

    aqi: float | None
    scale: str
    category: str
    assembly: str
    sports: str
    best_window: str
    parent_summary: str


def school_plan(report: AirReport) -> SchoolPlan:
    """Build today's school plan from the forecast."""
    aqi, scale, category = report.primary_aqi()
    best = report.best_hour_today()
    window = report.cleanest_window(2)
    best_window = ""
    if window is not None:
        best_window = f"{hour_label(window[0])}–{hour_label(window[1])}"
    elif best is not None:
        best_window = hour_label(best.time)
    if aqi is None:
        return SchoolPlan(
            aqi=None, scale=scale, category="Unavailable",
            assembly="No reading — keep assembly short and indoors if the "
                     "air looks hazy.",
            sports="No reading — keep sports light until data returns.",
            best_window=best_window,
            parent_summary=("No current air-quality reading is available "
                            "today. The school will keep outdoor time short "
                            "until data returns."),
        )
    # Thresholds on the primary (Indian) scale; US fallback uses 150/100.
    indian = scale.startswith("Indian")
    poor = 200 if indian else 150
    moderate = 100
    if aqi > poor:
        assembly = ("Hold assembly indoors today — the air is too poor for "
                    "a long outdoor gathering.")
        sports = ("Move all outdoor sports indoors today. No outdoor PT, "
                  "matches or practice.")
    elif aqi > moderate:
        assembly = ("Keep assembly short (under 10 minutes) and outdoors "
                    "only if the air looks clear.")
        sports = (f"Shorten outdoor sports and hold them in the cleanest "
                  f"window ({best_window}) if possible; keep sessions "
                  "light and watch for breathless children.")
    else:
        assembly = "Assembly outdoors as usual."
        sports = ("Outdoor sports as usual — the cleanest window today is "
                  f"{best_window}." if best_window else
                  "Outdoor sports as usual.")
    parent_summary = (
        f"Today's {scale} in {report.city.name} is {aqi:g} ({category}). "
        f"{assembly} {sports} Please send your child with a mask if they "
        "walk or cycle to school." if aqi > moderate else
        f"Today's {scale} in {report.city.name} is {aqi:g} ({category}). "
        "Outdoor school activities are running as usual today.")
    return SchoolPlan(aqi=aqi, scale=scale, category=category,
                      assembly=assembly, sports=sports,
                      best_window=best_window,
                      parent_summary=parent_summary)
