"""Low-emission daily routine: profile -> tailored plan with impact notes.

Every recommendation carries the signature "Why This, Why Now?" triple
(see planner/why.py): Why this? / Why now? / What impact? — computed from
the real hourly forecast wherever possible (for example, how much lower
the AQI is in the suggested window than right now). No recommendation is
invented: windows come from AirReport.cleanest_window / best_hour_today,
and advice text is driven by the primary AQI band (calculated Indian AQI, US AQI fallback) and sensitivity.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .api import AirReport
from .aqi import aqi_difference_pct
from .utils import hour_label
from .why import WhyNow

SENSITIVITIES = [
    "General",
    "Sensitive groups",
    "Asthma / respiratory condition",
    "Child",
    "Elderly",
    "Outdoor athlete",
]

# Indian transport first (the project is for India), then the rest.
COMMUTE_MODES = ["Metro", "Bus", "Auto-rickshaw", "Two-wheeler", "Cycle",
                 "Walk", "Car (petrol/diesel)", "Car (electric)", "Carpool",
                 "Work from home"]

HOUSEHOLD_TYPES = ["Flat / Apartment", "Independent house", "Shared / PG",
                   "Office"]

WORKPLACES = ["Office", "Hybrid (can work from home some days)",
              "Work from home"]

SENSITIVE_SET = {"Sensitive groups", "Asthma / respiratory condition",
                 "Child", "Elderly"}

# AQI above which outdoor exercise should move indoors / a mask is advised,
# by sensitivity. Indian limits follow CPCB bands (Moderate tops at 200,
# Satisfactory at 100); US limits follow the EPA bands (150 / 100).
EXERCISE_LIMITS_INDIAN = {
    "General": 200, "Sensitive groups": 100,
    "Asthma / respiratory condition": 100, "Child": 100, "Elderly": 100,
    "Outdoor athlete": 200,
}
MASK_LIMITS_INDIAN = dict(EXERCISE_LIMITS_INDIAN)
EXERCISE_LIMITS_US = {
    "General": 150, "Sensitive groups": 100,
    "Asthma / respiratory condition": 100, "Child": 100, "Elderly": 100,
    "Outdoor athlete": 150,
}
MASK_LIMITS_US = dict(EXERCISE_LIMITS_US)


def _primary(report: AirReport) -> tuple[float | None, bool, str]:
    """(value, is_indian_scale, category) for the report's primary AQI."""
    value, scale, category = report.primary_aqi()
    return value, scale.startswith("Indian"), category


@dataclass
class Profile:
    """The user's day: sensitivity, commute, work and exercise habits."""

    sensitivity: str = "General"
    commute_mode: str = "Metro"
    commute_km: float = 10.0
    workplace: str = "Office"
    household_type: str = "Flat / Apartment"
    work_start_hour: int = 9
    work_end_hour: int = 18
    exercises_outdoors: bool = True
    exercise_minutes: int = 30
    has_purifier: bool = False
    notes: str = ""

    def is_sensitive(self) -> bool:
        return self.sensitivity in SENSITIVE_SET

    def exercise_limit(self, indian: bool = True) -> int:
        table = EXERCISE_LIMITS_INDIAN if indian else EXERCISE_LIMITS_US
        return table.get(self.sensitivity, 200 if indian else 150)

    def mask_limit(self, indian: bool = True) -> int:
        table = MASK_LIMITS_INDIAN if indian else MASK_LIMITS_US
        return table.get(self.sensitivity, 200 if indian else 150)

    def can_work_from_home(self) -> bool:
        return self.workplace in ("Hybrid (can work from home some days)",
                                  "Work from home")


@dataclass
class PlanItem:
    """One recommendation: what to do, when, and its WhyNow triple."""

    title: str
    action: str
    impact: str
    window: str = ""
    done: bool = False
    why: WhyNow | None = None

    def why_or_default(self) -> WhyNow:
        """The item's WhyNow, or a fallback built from its impact text."""
        if self.why is not None:
            return self.why
        return WhyNow(why_this=self.action, why_now="Today's conditions.",
                      what_impact=self.impact)


@dataclass
class DayPlan:
    """The full tailored plan for today."""

    items: list[PlanItem] = field(default_factory=list)
    headline: str = ""
    aqi_now: float | None = None
    category: str = ""
    checklist: list[str] = field(default_factory=list)


def _pct_text(now: float | None, target: float | None) -> str:
    """'about 37% lower than right now' — or '' when numbers are missing."""
    if now is None or target is None or now <= 0:
        return ""
    pct = aqi_difference_pct(now, target)
    if pct < 0:
        return f"about {abs(pct)}% lower than right now"
    if pct > 0:
        return f"about {pct}% higher than right now"
    return "about the same as right now"


def _commute_item(profile: Profile, report: AirReport) -> PlanItem:
    mode = profile.commute_mode
    aqi, _indian, _category = _primary(report)
    best = report.best_hour_today()
    if mode == "Work from home":
        return PlanItem(
            "Commute — none today",
            "You work from home, so there is no commute exposure today.",
            "Zero commute emissions and zero roadside exposure — the lowest-"
            "emission option there is.",
            why=WhyNow(
                why_this="Working from home removes the trip entirely.",
                why_now="Every day you skip the commute is a zero-emission day.",
                what_impact="Zero commute emissions and zero roadside exposure.",
            ),
        )
    if mode in ("Cycle", "Walk"):
        window = ""
        why_this = ("Active travel adds no exhaust, but you breathe roadside "
                    "air directly, so timing matters.")
        why_now = "Travel near the cleanest hour of the day if you can."
        impact = why_this
        if best is not None and aqi is not None:
            window = f"{hour_label(best.time)} (cleanest hour today)"
            why_now = (f"The cleanest hour today is {hour_label(best.time)} "
                       f"(AQI {best.primary_aqi:g}), {_pct_text(aqi, best.primary_aqi)}.")
            impact += (f" Travelling near {hour_label(best.time)} puts you in "
                       f"air at AQI {best.primary_aqi:g}, {_pct_text(aqi, best.primary_aqi)}.")
        if aqi is not None and aqi > profile.mask_limit(indian=_indian):
            impact += (" With AQI this high, wear a well-fitting N95/FFP2 mask "
                       "for the trip.")
        return PlanItem("Commute — active travel",
                        f"Travel by {mode.lower()} if you can, and avoid the "
                        "busiest road where possible.", impact, window,
                        why=WhyNow(why_this=why_this, why_now=why_now,
                                   what_impact=impact))
    if mode == "Two-wheeler":
        return PlanItem(
            "Commute — two-wheeler",
            "Ride with a well-fitting helmet and an N95/FFP2 mask under it; "
            "avoid the busiest road where possible.",
            "A two-wheeler uses less fuel than a car, but you ride in "
            "traffic fumes directly — a mask cuts the particles you breathe.",
            why=WhyNow(
                why_this="Two-wheelers are fuel-efficient but leave you "
                         "exposed to roadside air.",
                why_now=("Today's AQI makes roadside exposure worth "
                         "protecting against."),
                what_impact="Lower fuel use than a car, plus a mask cuts the "
                            "particles you breathe on the ride.",
            ),
        )
    if mode == "Auto-rickshaw":
        return PlanItem(
            "Commute — auto-rickshaw",
            "Take the auto as planned; wear an N95/FFP2 mask on poor-air "
            "days, since autos are open to roadside air.",
            "An auto uses less fuel than a solo car and is easy to share, "
            "but it is open — a mask is the main protection you have.",
            why=WhyNow(
                why_this="Autos are low-fuel and flexible, but open to the air.",
                why_now="On today's AQI, a mask is the difference between "
                        "breathing roadside air filtered or unfiltered.",
                what_impact="Lower emissions than a solo car, with mask "
                            "protection against roadside particles.",
            ),
        )
    if mode in ("Metro", "Bus"):
        return PlanItem(
            f"Commute — {mode.lower()}",
            f"Take the {mode.lower()} as planned; wait indoors or in a "
            "covered area where possible.",
            "Public transport emits far less per passenger than a solo car "
            "trip, and waiting indoors keeps your exposure down on a "
            "poor-air day.",
            why=WhyNow(
                why_this=f"The {mode.lower()} is the lowest-emission way to "
                         "cover this distance.",
                why_now=("Rush-hour roads are the most polluted part of the "
                         "day; the metro/bus keeps you out of them."),
                what_impact="Far lower per-person emissions than a solo car, "
                            "and less time breathing traffic fumes.",
            ),
        )
    if mode == "Car (petrol/diesel)":
        return PlanItem(
            "Commute — car",
            "If you must drive, share the ride, keep windows closed and use "
            "recirculated air. Consider the metro or bus for one leg today.",
            "A shared or public trip roughly halves per-person exhaust versus "
            "driving alone, and closed windows with recirculation cut the "
            "particles you breathe inside the car.",
            why=WhyNow(
                why_this="A solo petrol/diesel car is the highest-emission "
                         "way to make this trip.",
                why_now=("Today's air is already loaded; one fewer car at "
                         "rush hour helps everyone breathe."),
                what_impact="Sharing or switching one leg roughly halves "
                            "per-person exhaust; closed windows cut the "
                            "particles you breathe inside.",
            ),
        )
    if mode == "Carpool":
        return PlanItem(
            "Commute — carpool",
            "Carpool as planned, windows closed, recirculated air on.",
            "Sharing the car splits per-person emissions across the passengers "
            "and takes a car off the road.",
            why=WhyNow(
                why_this="Carpooling splits one car's emissions across its "
                         "passengers.",
                why_now="Every shared seat is one fewer car in today's traffic.",
                what_impact="Lower per-person emissions and one fewer car on "
                            "the road.",
            ),
        )
    if mode == "Car (electric)":
        return PlanItem(
            "Commute — electric car",
            "Drive as planned, windows closed, recirculated air on.",
            "No tailpipe exhaust, so your trip adds no direct NO2 or exhaust "
            "particles — though road and tyre dust still matter.",
            why=WhyNow(
                why_this="An electric car adds no tailpipe exhaust.",
                why_now=("With today's AQI, keeping windows closed still "
                         "matters — the air outside is the problem, not your car."),
                what_impact="No direct NO2 or exhaust particles from your trip.",
            ),
        )
    return PlanItem(
        "Commute — public transport",
        "Take public transport as planned; wait indoors where possible.",
        "Public transport emits far less per passenger than a solo car trip.",
        why=WhyNow(
            why_this="Public transport is the lowest-emission way to cover "
                     "this distance.",
            why_now="Rush-hour roads are the most polluted part of the day.",
            what_impact="Far lower per-person emissions than a solo car.",
        ),
    )


def _exercise_item(profile: Profile, report: AirReport) -> PlanItem:
    aqi, _indian, _category = _primary(report)
    if not profile.exercises_outdoors:
        return PlanItem(
            "Exercise — indoors",
            f"Do your {profile.exercise_minutes} minutes indoors today.",
            "Indoor exercise keeps your breathing rate up without the outdoor "
            "particle load — the safest option on a poor-air day.",
            why=WhyNow(
                why_this="You exercise indoors, so outdoor air never enters "
                         "the picture.",
                why_now="Indoor exercise is the safest option on any "
                        "poor-air day.",
                what_impact="Full workout benefit with no outdoor particle load.",
            ),
        )
    window = report.cleanest_window(3)
    limit = profile.exercise_limit(indian=_indian)
    if aqi is not None and aqi > limit:
        if window is not None:
            start, end, avg = window
            impact = (f"That window averages AQI {avg:g}, "
                      f"{_pct_text(aqi, avg)} — still not clean, so keep it "
                      "light and stop if you feel breathless.")
            return PlanItem(
                "Exercise — move indoors, or use the cleanest window",
                f"AQI is {aqi:g} now, above your {limit} limit. Exercise "
                f"indoors, or if you go out, use {hour_label(start)}–"
                f"{hour_label(end)}.",
                impact,
                f"{hour_label(start)}–{hour_label(end)}",
                why=WhyNow(
                    why_this="Heavy breathing during exercise pulls far more "
                             "particles deep into the lungs.",
                    why_now=(f"Right now the AQI is {aqi:g}, above your "
                             f"{limit} limit; the cleanest window today is "
                             f"{hour_label(start)}–{hour_label(end)}."),
                    what_impact=impact,
                ),
            )
        impact = ("Heavy breathing during exercise pulls far more particles "
                  "deep into the lungs, so indoors is the safer choice today.")
        return PlanItem(
            "Exercise — indoors today",
            f"AQI is {aqi:g} now, above your {limit} limit, so exercise "
            "indoors today.",
            impact,
            why=WhyNow(
                why_this="Exercise means deep, fast breathing — the worst "
                         "time to breathe polluted air.",
                why_now=f"Right now the AQI is {aqi:g}, above your {limit} limit.",
                what_impact=impact,
            ),
        )
    if window is not None:
        start, end, avg = window
        impact = (f"That window averages AQI {avg:g}, {_pct_text(aqi, avg)} — "
                  "the cleanest stretch of the day for your lungs.")
        return PlanItem(
            "Exercise — outdoors in the cleanest window",
            f"Exercise outdoors {hour_label(start)}–{hour_label(end)} for "
            f"about {profile.exercise_minutes} minutes.",
            impact,
            f"{hour_label(start)}–{hour_label(end)}",
            why=WhyNow(
                why_this="Outdoor exercise is good for you — when the air "
                         "allows it.",
                why_now=(f"The cleanest window today is "
                         f"{hour_label(start)}–{hour_label(end)}."),
                what_impact=impact,
            ),
        )
    impact = ("Air quality is within your limit right now, so outdoor "
              "exercise is fine — just avoid the busiest traffic.")
    return PlanItem(
        "Exercise — outdoors",
        f"Exercise outdoors for about {profile.exercise_minutes} minutes, "
        "away from busy roads if you can.",
        impact,
        why=WhyNow(
            why_this="Outdoor exercise is good for you when the air allows it.",
            why_now="Air quality is within your limit right now.",
            what_impact=impact,
        ),
    )


def _ventilation_item(profile: Profile, report: AirReport) -> PlanItem:
    aqi, _indian, _category = _primary(report)
    best = report.best_hour_today()
    close_limit = 200 if _indian else 150
    if aqi is not None and aqi > close_limit:
        impact = (f"With AQI above {close_limit}, opening windows pulls the "
                  "outdoor pollution straight indoors; a purifier can cut "
                  "indoor PM2.5 by roughly half while it runs.")
        return PlanItem(
            "Ventilation — keep windows closed",
            "Keep windows closed today and run your purifier (if you have one) "
            "in the room you use most.",
            impact,
            why=WhyNow(
                why_this="When outdoor air is bad, the window is the main "
                         "way pollution gets indoors.",
                why_now=f"Right now the AQI is {aqi:g} — above "
                        f"{close_limit}, so opening up would import the problem.",
                what_impact=impact,
            ),
        )
    if best is not None and aqi is not None:
        impact = (f"At {hour_label(best.time)} the AQI is {best.primary_aqi:g}, "
                  f"{_pct_text(aqi, best.primary_aqi)} — the cheapest fresh air of "
                  "the day, with the least pollution coming in.")
        return PlanItem(
            "Ventilation — open windows at the cleanest hour",
            f"Air out the home for 20–30 minutes around {hour_label(best.time)}, "
            "then close up again.",
            impact,
            hour_label(best.time),
            why=WhyNow(
                why_this="A short, well-timed airing clears indoor CO2 and "
                         "cooking fumes.",
                why_now=(f"The cleanest hour today is "
                         f"{hour_label(best.time)} (AQI {best.primary_aqi:g})."),
                what_impact=impact,
            ),
        )
    impact = ("A short, well-timed airing clears indoor CO2 and cooking "
              "fumes without letting in the worst of the day's pollution.")
    return PlanItem(
        "Ventilation — air out briefly",
        "Air out the home for 20–30 minutes, ideally away from rush hour.",
        impact,
        why=WhyNow(
            why_this="Indoor air goes stale without fresh air.",
            why_now="Away from rush hour the outdoor air is at its cleanest.",
            what_impact=impact,
        ),
    )


def _outdoor_time_item(profile: Profile, report: AirReport) -> PlanItem:
    aqi, _indian, _category = _primary(report)
    worst = report.worst_hour_today()
    if aqi is None:
        impact = ("Without a current reading, the cautious choice is to limit "
                  "long outdoor exertion until data returns.")
        return PlanItem(
            "Outdoor time — no data",
            "No current AQI reading is available, so keep outdoor time short "
            "and check again later.",
            impact,
            why=WhyNow(
                why_this="Without a reading, caution is the only safe plan.",
                why_now="Data is unavailable right now.",
                what_impact=impact,
            ),
        )
    if aqi > (300 if _indian else 200):
        impact = (f"Above AQI {300 if _indian else 200} the health risk "
                  "rises for everyone, and a mask filters most PM2.5 — "
                  "unlike a cloth or surgical mask.")
        return PlanItem(
            "Outdoor time — stay in",
            "Keep outdoor time to essential trips only, and wear a "
            "well-fitting N95/FFP2 mask.",
            impact,
            why=WhyNow(
                why_this="Above AQI 200, even short outdoor time adds up.",
                why_now=f"Right now the AQI is {aqi:g} — in the "
                        f"{_category.lower()} range.",
                what_impact=impact,
            ),
        )
    if worst is not None and worst.primary_aqi is not None and worst.primary_aqi > aqi:
        impact = (f"The forecast peaks at AQI {worst.primary_aqi:g} around "
                  f"{hour_label(worst.time)} — planning around it keeps your "
                  "exposure down with no extra effort.")
        return PlanItem(
            "Outdoor time — avoid the worst hour",
            f"Do errands and outdoor chores before or after "
            f"{hour_label(worst.time)}, when the AQI peaks.",
            impact,
            hour_label(worst.time),
            why=WhyNow(
                why_this="Errands can move; the pollution peak cannot.",
                why_now=(f"The forecast peaks at AQI {worst.primary_aqi:g} around "
                         f"{hour_label(worst.time)}."),
                what_impact=impact,
            ),
        )
    impact = ("AQI is not high enough to restrict normal outdoor time — "
              "staying off the busiest roads still cuts your traffic-fume "
              "exposure.")
    return PlanItem(
        "Outdoor time — fine today",
        "Outdoor errands and chores are fine today; prefer quieter streets.",
        impact,
        why=WhyNow(
            why_this="Normal outdoor time is fine when the air allows it.",
            why_now=f"Right now the AQI is {aqi:g} — within a normal range.",
            what_impact=impact,
        ),
    )


def _mask_item(profile: Profile, report: AirReport) -> PlanItem | None:
    aqi, _indian, _category = _primary(report)
    if aqi is None or aqi <= profile.mask_limit(indian=_indian):
        return None
    impact = ("At this AQI a fitted N95/FFP2 filters most PM2.5; a cloth or "
              "surgical mask does not. The seal matters — no gaps at the nose.")
    return PlanItem(
        "Mask — wear one outdoors",
        "Wear a well-fitting N95/FFP2 mask for any time outdoors today.",
        impact,
        why=WhyNow(
            why_this="A fitted N95/FFP2 is the only common mask that filters "
                     "most PM2.5.",
            why_now=f"Right now the AQI is {aqi:g}, above your mask limit of "
                    f"{profile.mask_limit(indian=_indian)}.",
            what_impact=impact,
        ),
    )


def _morning_item(profile: Profile, report: AirReport) -> PlanItem:
    aqi, _indian, _category = _primary(report)
    best = report.best_hour_today()
    if aqi is not None and aqi > (200 if _indian else 150):
        action = ("Check today's AQI before stepping out, put your mask and "
                  "water bottle by the door, and run the purifier in the "
                  "room you use most.")
        impact = ("A one-minute check stops you walking into the worst air "
                  "unprepared, and a purifier running from the morning keeps "
                  "the room's PM2.5 down all day.")
        why_now = f"This morning's AQI is {aqi:g} — a poor-air morning."
    elif best is not None:
        action = (f"Check today's AQI, and plan outdoor time near "
                  f"{hour_label(best.time)}, the cleanest hour.")
        impact = ("A one-minute check lets you place the day's outdoor time "
                  "where the air is cleanest.")
        why_now = (f"The cleanest hour today is {hour_label(best.time)}.")
    else:
        action = "Check today's AQI before stepping out."
        impact = "A one-minute check keeps the day's plan honest."
        why_now = "A quick check each morning beats guessing."
    return PlanItem(
        "Morning routine — check before you step out",
        action, impact,
        why=WhyNow(
            why_this="Mornings set the day's exposure: commute, school run, "
                     "exercise all happen early.",
            why_now=why_now,
            what_impact=impact,
        ),
    )


def _evening_item(profile: Profile, report: AirReport) -> PlanItem:
    worst = report.worst_hour_today()
    _, _indian, _ = _primary(report)
    if (worst is not None and worst.primary_aqi is not None
            and worst.primary_aqi > (200 if _indian else 150)):
        action = (f"Close windows before the evening peak around "
                  f"{hour_label(worst.time)}, run the purifier while you "
                  "cook, and keep the evening indoors.")
        impact = ("Evening peaks are common in winter smog; closing up "
                  "before the peak keeps the day's worst air outside.")
        why_now = (f"The forecast peaks at AQI {worst.primary_aqi:g} around "
                   f"{hour_label(worst.time)}.")
    else:
        action = ("Close windows as the evening cools, run the purifier "
                  "while you cook, and check tomorrow's forecast before bed.")
        impact = ("Cooking is the biggest indoor particle source; a purifier "
                  "running while you cook keeps the evening's air cleaner.")
        why_now = "Evenings are cooking time — the biggest indoor source."
    return PlanItem(
        "Evening routine — close up before the peak",
        action, impact,
        why=WhyNow(
            why_this="Evenings combine cooking smoke with the day's second "
                     "pollution peak.",
            why_now=why_now,
            what_impact=impact,
        ),
    )


def _wfh_item(profile: Profile, report: AirReport) -> PlanItem | None:
    aqi, _indian, _category = _primary(report)
    if aqi is None or aqi <= (300 if _indian else 200):
        return None
    if not profile.can_work_from_home():
        return None
    if profile.commute_mode == "Work from home":
        return None
    impact = ("Skipping one commute on a very poor-air day avoids the day's "
              "biggest single dose of roadside air and saves the trip's "
              "emissions entirely.")
    return PlanItem(
        "Work from home today if you can",
        "If your work allows it, work from home today instead of commuting.",
        impact,
        why=WhyNow(
            why_this="The commute is usually the day's biggest dose of "
                     "roadside air.",
            why_now=f"Today's AQI is {aqi:g} ({_category.lower()}) — and your "
                    "work allows working from home.",
            what_impact=impact,
        ),
    )


def _daily_checklist(profile: Profile, report: AirReport) -> list[str]:
    """Daily sustainability checklist, tailored to the profile."""
    items = [
        "Checked today's AQI before going out",
        "Used the lowest-emission commute available today",
        "Ventilated at the cleanest hour (or kept windows closed on a poor-air day)",
        "Combined errands into one trip",
    ]
    if profile.has_purifier:
        items.append("Ran the purifier in the room I used most")
    if profile.exercises_outdoors:
        items.append("Exercised in the cleanest window of the day")
    items.append("Checked tomorrow's forecast before bed")
    return items


def build_day_plan(profile: Profile, report: AirReport) -> DayPlan:
    """Build the tailored low-emission plan for today."""
    items = [
        _morning_item(profile, report),
        _commute_item(profile, report),
        _exercise_item(profile, report),
        _ventilation_item(profile, report),
        _outdoor_time_item(profile, report),
        _evening_item(profile, report),
    ]
    mask = _mask_item(profile, report)
    if mask is not None:
        items.append(mask)
    wfh = _wfh_item(profile, report)
    if wfh is not None:
        items.append(wfh)
    aqi, _indian, category = _primary(report)
    if aqi is None:
        headline = ("No current AQI reading right now — the plan below is "
                    "cautious by default.")
    else:
        scale = "Indian AQI (CPCB)" if _indian else "US AQI"
        headline = (
            f"{scale} {aqi:g} ({category}) in {report.city.name} today. "
            f"Your plan is tailored for: {profile.sensitivity.lower()}."
        )
    return DayPlan(items=items, headline=headline, aqi_now=aqi,
                   category=category,
                   checklist=_daily_checklist(profile, report))
