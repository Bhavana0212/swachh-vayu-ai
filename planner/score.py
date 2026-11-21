"""Environmental Impact Score: daily decisions, estimated impact.

A transparent 0–100 score from the user's own inputs — commute mode,
habits done, checklist ticks and swaps adopted — with a visible breakdown
so the number can be checked. It is a motivational estimate, not a
measurement of real emissions.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .alternatives import KG_CO2_PER_KM

# Commute points (out of 30): cleaner modes score higher.
COMMUTE_POINTS = {
    "Work from home": 30, "Cycle": 30, "Walk": 30,
    "Metro": 27, "Bus": 24, "Carpool": 20,
    "Car (electric)": 20, "Two-wheeler": 18,
    "Auto-rickshaw": 15, "Car (petrol/diesel)": 8,
}


@dataclass
class ImpactScore:
    """Score breakdown: total plus each component, with a grade."""

    total: int
    commute_points: int
    habits_points: int
    checklist_points: int
    swaps_points: int
    grade: str
    suggestions: list[str] = field(default_factory=list)


def grade_for(total: int) -> str:
    """Grade label for a score total."""
    if total >= 80:
        return "Clean-air champion"
    if total >= 60:
        return "On track"
    if total >= 40:
        return "Getting going"
    return "Just starting"


def impact_score(commute_mode: str, habits_done_this_week: int,
                 checklist_done: int, checklist_total: int,
                 swaps_adopted: int) -> ImpactScore:
    """Compute the score from the user's inputs (all counts are the user's own)."""
    commute = COMMUTE_POINTS.get(commute_mode, 15)
    habits = min(30, max(0, habits_done_this_week) * 3)
    if checklist_total > 0:
        checklist = round(20 * min(checklist_done, checklist_total)
                          / checklist_total)
    else:
        checklist = 0
    swaps = min(20, max(0, swaps_adopted) * 5)
    total = min(100, commute + habits + checklist + swaps)
    suggestions = []
    if commute < 20:
        suggestions.append(
            "Your commute is your biggest lever — try the metro, bus or a "
            "shared ride for one trip a week (see What If).")
    if habits < 15:
        suggestions.append(
            "Log one sustainable habit a day in the Challenge — small daily "
            "actions add up fastest.")
    if checklist_total and checklist_done < checklist_total:
        suggestions.append(
            "Tick off today's sustainability checklist on the My Routine page.")
    if swaps < 10:
        suggestions.append(
            "Adopt one swap from Sustainable Alternatives this week.")
    if not suggestions:
        suggestions.append(
            "You are doing well — keep the streak going and help someone "
            "else start.")
    return ImpactScore(total=total, commute_points=commute,
                       habits_points=habits, checklist_points=checklist,
                       swaps_points=swaps, grade=grade_for(total),
                       suggestions=suggestions)


def co2_savings_series(commute_km: float, days_per_week: int = 5) -> dict[str, float]:
    """Weekly CO2 saving (kg) if the user switched car -> metro, per weekday.

    Returns a day -> kg mapping for a simple bar chart. Assumption: petrol
    car 0.17 kg CO2/km vs metro 0.03, return trips.
    """
    per_day = ((KG_CO2_PER_KM["Car (petrol/diesel)"] - KG_CO2_PER_KM["Metro"])
               * max(commute_km, 0.0) * 2)
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    return {day: round(per_day, 2) if i < max(days_per_week, 0) else 0.0
            for i, day in enumerate(days)}
