"""Smart Activity Planner: "Is it safe to...?" answered from the forecast.

The user picks an activity and a time; the app answers from the real
hourly forecast (indicative Indian AQI per hour, US AQI fallback),
suggests a better time when one exists, and explains the exposure.
Verdicts are conservative and non-diagnostic.
"""
from __future__ import annotations

from dataclasses import dataclass

from .api import AirReport
from .aqi import us_band
from .indian_aqi import category_for as indian_category_for
from .routine import Profile
from .utils import hour_label
from .why import WhyNow

# Activity -> (intensity: low/medium/high, typical duration note)
ACTIVITIES: dict[str, tuple[str, str]] = {
    "Morning walk": ("low", "about 30–45 minutes, easy pace"),
    "Walking": ("low", "about 30–45 minutes, easy pace"),
    "Running": ("high", "about 30–60 minutes, hard breathing"),
    "Outdoor run": ("high", "about 30–60 minutes, hard breathing"),
    "Cycling": ("high", "about 30–60 minutes, hard breathing"),
    "Yoga": ("low", "about 45 minutes, gentle breathing"),
    "Yoga in the park": ("low", "about 45 minutes, gentle breathing"),
    "Outdoor gym": ("medium", "about 45 minutes, moderate effort"),
    "Gardening": ("low", "about 30–60 minutes, light effort"),
    "Children playing outside": ("medium", "about 1 hour, active play"),
    "Children's outdoor play": ("medium", "about 1 hour, active play"),
    "Outdoor work / labour": ("high", "several hours, sustained effort"),
}

# Intensity shifts the safe limit: hard breathing lowers it, gentle raises it.
INTENSITY_SHIFT = {"low": 25, "medium": 0, "high": -25}


@dataclass
class SafetyVerdict:
    """The answer to 'Is it safe to do X at this hour?'"""

    activity: str
    hour: int
    aqi_at_hour: float | None
    verdict: str  # "Safe" | "Caution" | "Avoid" | "No data"
    advice: str
    better_time: str = ""
    why: WhyNow | None = None
    scale: str = "Indian AQI (CPCB)"


def hourly_aqi_at(report: AirReport, hour: int) -> float | None:
    """Forecast primary AQI at a given hour today (None when unavailable)."""
    for point in report.today_hours():
        try:
            if int(point.time[11:13]) == hour:
                return point.primary_aqi
        except (ValueError, IndexError):
            continue
    return None


def _category(aqi: float, indian: bool) -> str:
    if indian:
        return indian_category_for(aqi)[0]
    return us_band(aqi).category


def _limit_for(profile: Profile, intensity: str, indian: bool) -> int:
    base = profile.exercise_limit(indian=indian)
    return max(50, base + INTENSITY_SHIFT.get(intensity, 0))


def assess(activity: str, hour: int, profile: Profile,
           report: AirReport) -> SafetyVerdict:
    """Assess an activity at an hour from the hourly forecast."""
    intensity, duration = ACTIVITIES.get(activity, ("medium", ""))
    aqi = hourly_aqi_at(report, hour)
    best = report.best_hour_today()
    better = ""
    if best is not None and best.primary_aqi is not None:
        better = hour_label(best.time)
    _value, scale, _cat = report.primary_aqi()
    indian = scale.startswith("Indian")
    if aqi is None:
        return SafetyVerdict(
            activity=activity, hour=hour, aqi_at_hour=None,
            verdict="No data",
            advice=("No forecast is available for that hour, so keep the "
                    "activity short and check again later."),
            better_time=better,
            why=WhyNow(
                why_this="Without a forecast, caution is the only safe plan.",
                why_now="No hourly data is available for that time.",
                what_impact="Keeping it short limits exposure until data returns.",
            ),
            scale=scale,
        )
    limit = _limit_for(profile, intensity, indian)
    category = _category(aqi, indian)
    if aqi <= limit:
        verdict = "Safe"
        advice = (f"AQI {aqi:g} ({category}) at {hour_label(hour)} is "
                  f"within your limit of {limit} for this activity. Go ahead"
                  f" — {duration} — and prefer quieter streets.")
    elif aqi <= limit + 50:
        verdict = "Caution"
        advice = (f"AQI {aqi:g} ({category}) at {hour_label(hour)} is "
                  f"above your limit of {limit} for this activity. Shorten "
                  f"it, keep it light, and stop if you feel breathless.")
    else:
        verdict = "Avoid"
        advice = (f"AQI {aqi:g} ({category}) at {hour_label(hour)} is "
                  f"well above your limit of {limit} for this activity. "
                  "Move it indoors or to a cleaner time.")
    if better and verdict != "Safe":
        advice += f" The cleanest hour today is {better}."
    why_now = (f"At {hour_label(hour)} the forecast {scale} is {aqi:g} "
               f"({category}); your limit for {activity.lower()} is {limit}.")
    if verdict == "Safe":
        impact = ("Exercising within your limit keeps particle exposure low "
                  "while you get the full benefit of the activity.")
    elif verdict == "Caution":
        impact = ("Shortening and lightening the activity cuts the total "
                  "particles you breathe during it.")
    else:
        impact = ("Moving indoors or to a cleaner time avoids the day's "
                  "worst exposure for this activity.")
    return SafetyVerdict(
        activity=activity, hour=hour, aqi_at_hour=aqi, verdict=verdict,
        advice=advice, better_time=better,
        why=WhyNow(
            why_this=f"{activity} means {duration}, and breathing rate "
                     "decides how much pollution reaches your lungs.",
            why_now=why_now,
            what_impact=impact,
        ),
        scale=scale,
    )
