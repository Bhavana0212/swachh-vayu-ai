"""Indoor Air Intelligence — room-by-room planning, cooking, sources,
ventilation timing and the Home Clean-Air Score.

All outputs are estimates and advice, never measurements. Room guidance
reuses the indoor estimator from planner/indoor.py with per-room inputs.
"""
from __future__ import annotations

from dataclasses import dataclass

from .api import AirReport
from .indoor import estimate_indoor_pm25
from .utils import hour_label

ROOMS = ["Bedroom", "Kitchen", "Living room", "Children's room",
         "Study room"]

ROOM_PROFILES: dict[str, dict[str, str]] = {
    "Bedroom": {
        "risk": ("You spend 7–8 hours here, so overnight air matters most."),
        "advice": ("Run the purifier on low overnight if you have one; keep "
                   "the door closed to hold clean air in; change bedding "
                   "weekly to cut dust."),
    },
    "Kitchen": {
        "risk": ("Cooking is the biggest indoor particle source — frying "
                 "can push indoor PM2.5 far above outdoor levels."),
        "advice": ("Always switch the chimney/exhaust on BEFORE cooking; "
                   "keep it running 15 minutes after; prefer lids and "
                   "lower-heat cooking; open a window only when outdoor "
                   "air is cleaner."),
    },
    "Living room": {
        "risk": ("The room most people share, with the most door and window "
                 "openings to outdoor air."),
        "advice": ("This is the best room for the purifier if you have one; "
                   "keep shoes at the door; vacuum or wet-mop rather than "
                   "dry-sweeping."),
    },
    "Children's room": {
        "risk": ("Children breathe faster and spend time on the floor, where "
                 "dust settles."),
        "advice": ("No incense or mosquito coils in this room; wet-mop the "
                   "floor; keep soft toys washed; purifier on low during "
                   "sleep if available."),
    },
    "Study room": {
        "risk": ("Long sitting hours with windows often closed for quiet — "
                 "CO2 builds up and concentration drops."),
        "advice": ("Air the room briefly at the cleanest hour; keep the "
                   "window cracked during study if outdoor air allows; "
                   "take outdoor breaks when the AQI is moderate."),
    },
}

COOKING_TIPS = [
    ("Use the chimney / exhaust fan every time",
     "Switch it on before you start cooking and keep it running 15 minutes "
     "after. It is the single biggest cut to cooking smoke."),
    ("Cook with lids on",
     "Lids trap steam and oil smoke at the pan instead of letting them fill "
     "the room."),
    ("Prefer low-oil, low-smoke methods",
     "Steaming, boiling and pressure cooking release far fewer particles "
     "than deep-frying and high-heat tadka."),
    ("Ventilate smartly",
     "Open a kitchen window only when outdoor AQI is better than indoor — "
     "check the Ventilation Timing Advisor below."),
    ("Clean the chimney filter monthly",
     "A clogged filter barely extracts; a clean one can cut cooking smoke "
     "by more than half."),
]

SOURCE_CHECKLIST = [
    ("Incense sticks (agarbatti)", "Burning incense releases fine particles "
     "and VOCs — use sparingly and ventilate afterwards."),
    ("Mosquito coils", "Coils release PM2.5 and chemicals all night — a "
     "mesh on windows or a plug-in vaporiser is cleaner."),
    ("Candles", "Scented candles add soot and fragrance chemicals; use "
     "briefly and ventilate."),
    ("Smoking indoors", "The single worst indoor source — smoke outdoors, "
     "away from windows and doors."),
    ("Cleaning chemicals", "Strong sprays and phenyl release VOCs — use "
     "diluted, ventilate while cleaning, and prefer milder cleaners."),
    ("Cooking fumes", "See the Cooking Advisor above — chimney first, "
     "lids on, lower heat."),
    ("Dust from sweeping", "Dry sweeping throws settled dust back into the "
     "air — wet-mop or vacuum instead."),
    ("Damp / mould", "Damp corners grow mould, which worsens breathing — "
     "fix leaks and air damp rooms in dry weather."),
]


@dataclass
class RoomPlan:
    """Per-room estimate + guidance."""

    room: str
    estimated_pm25: float
    category: str
    risk: str
    advice: str


def room_plan(room: str, outdoor_pm25: float,
              purifier: bool = False) -> RoomPlan:
    """Estimate + guidance for one room.

    Kitchen and children's room get higher source loads in the model;
    other rooms use the standard model.
    """
    profile = ROOM_PROFILES.get(room, ROOM_PROFILES["Living room"])
    cooking = "Frying / grilling" if room == "Kitchen" else "No cooking right now"
    ventilation = ("Windows open" if room == "Kitchen"
                   else "Windows cracked / trickle vent")
    estimate = estimate_indoor_pm25(outdoor_pm25, ventilation, purifier,
                                    cooking)
    return RoomPlan(room=room, estimated_pm25=estimate.estimated_pm25,
                    category=estimate.risk_category, risk=profile["risk"],
                    advice=profile["advice"])


def ventilation_advice(report: AirReport) -> dict[str, str]:
    """When to open windows today, from the hourly forecast."""
    best = report.best_hour_today()
    worst = report.worst_hour_today()
    aqi, scale, category = report.primary_aqi()
    if aqi is None:
        return {
            "verdict": "No data — air out briefly away from rush hour",
            "detail": ("No current reading is available, so the cautious "
                       "choice is a short airing away from traffic hours."),
            "best_time": "", "worst_time": "",
        }
    if aqi > 200:
        return {
            "verdict": "Keep windows closed today",
            "detail": (f"{scale} {aqi:g} ({category}) — opening windows "
                       "would bring outdoor pollution straight in. Use the "
                       "purifier and the chimney fan instead."),
            "best_time": hour_label(best.time) if best else "",
            "worst_time": hour_label(worst.time) if worst else "",
        }
    if best is not None and best.primary_aqi is not None:
        return {
            "verdict": f"Open windows around {hour_label(best.time)}",
            "detail": (f"The cleanest hour today is {hour_label(best.time)} "
                       f"({scale} {best.primary_aqi:g}). Air out for 20–30 "
                       "minutes then, cross-ventilate (two windows on "
                       "opposite sides), and close up again."),
            "best_time": hour_label(best.time),
            "worst_time": hour_label(worst.time) if worst else "",
        }
    return {
        "verdict": "Air out briefly, away from rush hour",
        "detail": ("No hourly forecast is available; a short airing away "
                   "from traffic hours is the safe default."),
        "best_time": "", "worst_time": "",
    }


# Home Clean-Air Score: 0–100 from five honest inputs (each 0–20).
def home_clean_air_score(ventilation_good: bool, purifier: bool,
                         chimney_used: bool, sources_low: bool,
                         dust_controlled: bool) -> tuple[int, str, list[str]]:
    """Score + verdict + improvement checklist for the home.

    Returns (score, verdict, improvements). The score reflects habits the
    user reports — it is not a measurement.
    """
    score = 0
    improvements = []
    if ventilation_good:
        score += 20
    else:
        improvements.append("Ventilate at the cleanest hour of the day")
    if purifier:
        score += 20
    else:
        improvements.append("Consider a HEPA purifier for the room you "
                            "use most (see the Equipment Guide)")
    if chimney_used:
        score += 20
    else:
        improvements.append("Use the chimney/exhaust fan every time you cook")
    if sources_low:
        score += 20
    else:
        improvements.append("Cut indoor sources: no incense or coils in "
                            "bedrooms, smoke outdoors only")
    if dust_controlled:
        score += 20
    else:
        improvements.append("Wet-mop or vacuum instead of dry sweeping")
    if score >= 80:
        verdict = "Excellent — your home habits are protecting your air well."
    elif score >= 60:
        verdict = "Good — a few habits are worth tightening."
    elif score >= 40:
        verdict = "Fair — the checklist below would make a real difference."
    else:
        verdict = "Needs attention — start with ventilation and cooking."
    return score, verdict, improvements
