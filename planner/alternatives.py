"""Sustainable alternatives: swaps with honest impact estimates.

Every swap carries an impact note and a local practicality note.
Quantified numbers are simple estimates with their assumption stated in
the note (for example, the per-km emission factor used) — they are
planning estimates, not measurements.
"""
from __future__ import annotations

from dataclasses import dataclass

# Simple emission factors used for estimates (assumptions stated in the UI).
# Petrol/diesel car ~0.17 kg CO2 per km (single occupant); metro ~0.03;
# bus ~0.05; auto-rickshaw ~0.08; two-wheeler ~0.06; cycling/walking 0;
# EV ~0.05 (grid average, varies by country).
KG_CO2_PER_KM = {
    "Car (petrol/diesel)": 0.17,
    "Car (electric)": 0.05,
    "Metro": 0.03,
    "Bus": 0.05,
    "Auto-rickshaw": 0.08,
    "Two-wheeler": 0.06,
    "Carpool": 0.085,
    "Cycle": 0.0,
    "Walk": 0.0,
    "Work from home": 0.0,
}


@dataclass
class Swap:
    """One sustainable alternative."""

    category: str
    title: str
    action: str
    impact: str
    why_this: str = ""
    practicality: str = ""

    def why_or_default(self) -> str:
        """The 'Why this?' line, or a fallback from the action."""
        return self.why_this or self.action


def commute_swap(profile_commute: str, commute_km: float) -> Swap | None:
    """Best lower-emission commute swap for the user's current mode."""
    if profile_commute == "Work from home":
        return None
    current_factor = KG_CO2_PER_KM.get(profile_commute, 0.17)
    if profile_commute in ("Cycle", "Walk"):
        return Swap(
            "Transport",
            "Keep the active commute",
            "Your commute already adds no exhaust — keep it up, and use the "
            "cleanest-hour timing from your routine on poor-air days.",
            "Zero tailpipe emissions, every single day.",
            why_this="Active travel is already the cleanest way to move.",
            practicality="Works best for short trips; on poor-air days, "
                         "time it to the cleanest hour and wear a mask.",
        )
    if profile_commute in ("Metro", "Bus"):
        return Swap(
            "Transport",
            "One active leg a week",
            "Walk or cycle one leg of one trip a week where it is safe.",
            "Small direct saving, but it builds the habit and cuts your "
            "exposure to the busiest traffic.",
            why_this="You already use public transport — the next step is "
                     "one active leg.",
            practicality="Easy in cities with safe footpaths or cycle lanes; "
                         "skip it on very poor-air days.",
        )
    # Car, auto, two-wheeler, carpool -> metro/bus.
    saving_per_day = (current_factor - 0.03) * max(commute_km, 0.0) * 2
    return Swap(
        "Transport",
        "Swap one car trip a week for metro / bus",
        "Take the metro or bus for one return trip a week instead of the car.",
        f"At {commute_km:g} km each way, one swapped return trip saves about "
        f"{saving_per_day:.1f} kg CO2 (assuming ~0.17 kg CO2/km for a petrol "
        "car and ~0.03 for metro per passenger) and one car off the road "
        "at rush hour.",
        why_this="Public transport carries the same trip for a fraction of "
                 "the per-person emissions.",
        practicality="Best where metro/bus service is frequent; check the "
                     "route once and it becomes routine.",
    )


TRANSPORT_SWAPS: list[Swap] = [
    Swap("Transport", "Combine errands into one trip",
         "Plan errands as a single loop instead of several separate trips.",
         "Fewer cold starts and fewer kilometres — a cold engine pollutes "
         "most in its first few minutes, so one trip beats three short ones.",
         why_this="Most short trips are the dirtiest per kilometre.",
         practicality="Works everywhere; a shared family errand list helps."),
    Swap("Transport", "Share the ride",
         "Carpool with a colleague or neighbour for regular trips.",
         "Two people in one car roughly halves per-person emissions and "
         "takes a car off the road.",
         why_this="An empty seat is wasted fuel.",
         practicality="Easiest for fixed routines like office or school runs."),
    Swap("Transport", "Keep tyres pumped and the car serviced",
         "Check tyre pressure monthly and keep up with servicing.",
         "Under-inflated tyres raise fuel use by a few percent — free money "
         "and fewer emissions for a two-minute check.",
         why_this="A badly kept car burns more fuel for the same trip.",
         practicality="Any fuel station can check pressure in two minutes."),
]

HOME_SWAPS: list[Swap] = [
    Swap("Home", "Switch the last bulbs to LED",
         "Replace remaining old bulbs with LEDs, starting with the rooms you "
         "use most.",
         "An LED uses about 80% less electricity than an old bulb for the "
         "same light — and less electricity means less power-plant pollution.",
         why_this="Lighting is the easiest energy saving in any home.",
         practicality="LEDs are widely available and pay for themselves in "
                      "months."),
    Swap("Home", "Cook with a lid and the right ring",
         "Match the pot to the ring, use a lid, and turn the heat down once "
         "it boils.",
         "Less gas or electricity per meal, and less heat and moisture "
         "dumped into the kitchen air.",
         why_this="An uncovered pot wastes heat — and fuel — every minute.",
         practicality="No cost, no equipment; just a habit change."),
    Swap("Home", "Wash cold, hang dry",
         "Wash clothes in cold water and air-dry them when you can.",
         "Most of a wash's energy goes to heating water and tumble-drying — "
         "cold washing and line drying cut both sharply.",
         why_this="Heating water is the expensive part of laundry.",
         practicality="Easy in warm, dry weather; use a covered balcony or "
                      "indoor rack in the monsoon."),
    Swap("Home", "Run the purifier only where you are",
         "Run the purifier in the occupied room, on a timer, instead of "
         "all day everywhere.",
         "Same clean air where it matters, less electricity — a purifier "
         "uses roughly 30–60 W while running.",
         why_this="A purifier only cleans the room it is in.",
         practicality="A simple plug timer does the job automatically."),
]

FOOD_SWAPS: list[Swap] = [
    Swap("Food", "One meat-free day a week",
         "Cook one plant-based day a week — lentils, beans, vegetables.",
         "Red meat has a far higher footprint than plant protein; one day a "
         "week is a real, painless cut — roughly 0.5–1 kg CO2e saved per "
         "person per meat-free day (estimate, varies by meal).",
         why_this="What we eat is one of the biggest household footprints.",
         practicality="Indian cooking already has a rich plant-based menu — "
                      "dal, sabzi, chole need no new skills."),
    Swap("Food", "Buy seasonal and local first",
         "Choose in-season, local produce over air-freighted out-of-season "
         "items.",
         "Air-freighted food can carry 10–50x the transport emissions of "
         "local produce — and seasonal food is usually cheaper too.",
         why_this="Food miles are invisible until you look for them.",
         practicality="Local markets and mandis make this easy and cheaper."),
    Swap("Food", "Cut food waste",
         "Plan portions, use leftovers, and store food properly.",
         "Wasted food wastes all the energy, water and transport that went "
         "into it — and rotting food releases methane.",
         why_this="A third of food is wasted; every saved meal saves its "
                  "whole footprint.",
         practicality="A weekly meal plan and proper storage boxes help."),
]

SHOPPING_SWAPS: list[Swap] = [
    Swap("Shopping", "Carry reusables",
         "Keep a cloth bag, a water bottle and a tiffin in your day bag.",
         "One reusable bag replaces hundreds of single-use ones a year; a "
         "bottle replaces a daily plastic bottle.",
         why_this="Single-use items are used for minutes and last centuries.",
         practicality="Keep the kit by the door so it becomes automatic."),
    Swap("Shopping", "Buy less, buy durable",
         "Choose durable goods over the cheapest option, and repair before "
         "replacing.",
         "Making things is most of their footprint — a longer life means "
         "fewer things made.",
         why_this="The greenest product is the one you do not have to buy.",
         practicality="Local repair shops handle most electronics and "
                      "footwear cheaply."),
    Swap("Shopping", "Waste less, segregate more",
         "Segregate dry and wet waste, compost kitchen waste if you can.",
         "Segregated waste recycles better; composted food waste avoids "
         "landfill methane.",
         why_this="Mixed waste mostly ends up buried or burned.",
         practicality="Two bins and a compost pot are enough to start."),
]

ALL_SWAPS: list[Swap] = (TRANSPORT_SWAPS + HOME_SWAPS + FOOD_SWAPS
                         + SHOPPING_SWAPS)


def swaps_for(profile_commute: str, commute_km: float) -> list[Swap]:
    """All swaps, with the tailored commute swap first."""
    result: list[Swap] = []
    tailored = commute_swap(profile_commute, commute_km)
    if tailored is not None:
        result.append(tailored)
    result.extend(ALL_SWAPS)
    return result


def weekly_co2_saving_kg(commute_km: float, days_per_week: int = 5) -> float:
    """Estimated weekly CO2 saved by switching car -> metro, in kg.

    Assumption: petrol car 0.17 kg CO2/km vs metro 0.03, return trips.
    """
    per_day = (KG_CO2_PER_KM["Car (petrol/diesel)"]
               - KG_CO2_PER_KM["Metro"]) * max(commute_km, 0.0) * 2
    return round(per_day * max(days_per_week, 0), 1)


def monthly_co2_saving_kg(commute_km: float, days_per_week: int = 5) -> float:
    """Estimated monthly CO2 saved (weekly saving x ~4.33 weeks)."""
    return round(weekly_co2_saving_kg(commute_km, days_per_week) * 4.33, 1)
