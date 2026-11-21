"""Indoor air: hacks checklist, estimator and equipment guide.

"Indoor Air Intelligence": the estimator is a simple, documented box model —
it is an ESTIMATE, never a measurement, and the UI labels it that way with
its assumptions and uncertainty stated. Parameters are shown to the user so
the number can be checked, not trusted blindly.
"""
from __future__ import annotations

from dataclasses import dataclass

# Fraction of outdoor PM2.5 that gets indoors, by ventilation state.
VENTILATION_FACTORS = {
    "Windows closed": 0.35,
    "Windows cracked / trickle vent": 0.60,
    "Windows open": 0.90,
}

# Fraction of indoor PM2.5 a running purifier removes (HEPA, sized room).
PURIFIER_REDUCTION = 0.55

# Extra indoor PM2.5 (ug/m3) added while cooking, by stove type.
COOKING_ADDITION = {
    "No cooking right now": 0.0,
    "Electric / induction cooking": 8.0,
    "Gas cooking": 18.0,
    "Frying / grilling": 30.0,
}

# Cooking frequency scales the cooking addition (per-day cooking load).
COOKING_FREQUENCY_FACTORS = {
    "Once today": 1.0,
    "Twice today": 1.5,
    "Three or more times today": 2.0,
}

# Smoking indoors adds a large, uncertain amount (model assumption).
SMOKING_ADDITION = 40.0

# Extra PM2.5 from activity/resuspension per occupant beyond the first two.
OCCUPANT_ADDITION = 2.0

# Room-size adjustment: small rooms concentrate indoor sources more.
ROOM_SIZE_FACTORS = {
    "Small (under 150 sq ft)": 1.15,
    "Medium (150–400 sq ft)": 1.0,
    "Large (over 400 sq ft)": 0.9,
}

ASSUMPTIONS_TEXT = (
    "Assumptions: outdoor PM2.5 enters at 35% (windows closed), 60% "
    "(cracked) or 90% (open); a running HEPA purifier removes about 55%; "
    "cooking adds 8 (electric), 18 (gas) or 30 (frying) µg/m³; smoking "
    "indoors adds about 40 µg/m³; each occupant beyond two adds about "
    "2 µg/m³. Uncertainty is high — roughly ±50% or more. This is a "
    "planning estimate, never a measurement and never a substitute for a "
    "sensor."
)

# Indoor risk categories from the ESTIMATED indoor PM2.5 (ug/m3).
RISK_BANDS: list[tuple[float, float, str, str]] = [
    (0.0, 12.0, "Low",
     "Estimated indoor air is in a healthy range. Keep doing what works."),
    (12.0, 35.0, "Moderate",
     "Estimated indoor air is acceptable but could be better — run the "
     "purifier or ventilate at the cleanest hour."),
    (35.0, 55.0, "High",
     "Estimated indoor air is elevated. Run the purifier, keep windows "
     "closed on a poor-air day, and extract cooking fumes at the source."),
    (55.0, 10000.0, "Very high",
     "Estimated indoor air is poor. Run the purifier on high, avoid "
     "smoking and incense indoors, and ventilate only at the cleanest hour."),
]

# Indoor hacks: (title, what to do, why this?, what impact?)
INDOOR_HACKS: list[tuple[str, str, str, str]] = [
    ("Run the purifier in the room you use most",
     "Run a HEPA purifier on medium/high for at least 1–2 hours in the room "
     "where you spend the most time, doors closed.",
     "A purifier is the only indoor tool that actively removes particles.",
     "A well-sized HEPA purifier can cut indoor PM2.5 by roughly half "
     "while it runs."),
    ("Ventilate at the cleanest hour, not rush hour",
     "Open windows for 20–30 minutes at today's cleanest hour (see the "
     "dashboard), then close up again.",
     "Fresh air is needed, but its pollution load depends entirely on when "
     "you open up.",
     "The same airing at the cleanest hour can halve the pollution that "
     "comes in versus rush hour."),
    ("Cook with the extractor on, lid on",
     "Always run the extractor (or open a window briefly) when cooking, "
     "especially frying or gas cooking.",
     "Cooking is the biggest indoor particle source in most homes.",
     "Extraction at the source removes most cooking particles before they "
     "spread through the home."),
    ("Damp-dust and vacuum with a HEPA filter",
     "Wipe surfaces with a damp cloth and vacuum with a HEPA-filtered "
     "vacuum; avoid dry sweeping.",
     "Settled dust becomes airborne dust the moment it is disturbed.",
     "Damp cleaning removes dust instead of pushing it back into the air "
     "you breathe."),
    ("Keep humidity 40–60%",
     "Use a hygrometer; ventilate or dehumidify if it stays above 60%.",
     "Damp air grows mould and dust mites; very dry air irritates airways.",
     "Staying in range cuts mould and mite growth without drying out "
     "airways."),
    ("Keep shoes at the door",
     "Leave outdoor shoes by the entrance and wipe pets' paws after walks.",
     "Shoes carry road dust, pollen and particles straight inside.",
     "Less tracked-in dust means less of it ends up in the air you breathe."),
    ("No smoking or incense indoors",
     "Smoke, incense and candles indoors raise PM2.5 sharply — skip them on "
     "poor-air days.",
     "One incense stick can push a room's PM2.5 above outdoor levels.",
     "Skipping indoor smoke removes one of the largest single indoor "
     "particle spikes."),
    ("Plants help mood, not PM",
     "Enjoy houseplants for the greenery — but do not rely on them to clean "
     "the air.",
     "Plants are lovely, but studies show they remove a negligible amount "
     "of PM2.5 in a real room.",
     "Honest note: a purifier or good ventilation does the real work; "
     "plants do the mood work."),
]

# Clean Air Equipment Guide — EDUCATIONAL ONLY, not a medical prescription.
EQUIPMENT_GUIDE: list[tuple[str, str]] = [
    ("N95 / FFP2 masks",
     "A well-fitting N95 (US) or FFP2 (Europe) mask filters most PM2.5. "
     "The seal matters more than the brand — no gaps at the nose or "
     "cheeks. Replace when dirty, damp or hard to breathe through. "
     "Surgical and cloth masks do not seal, so fine particles leak around "
     "them. Children and people with breathing difficulties should get "
     "advice before using a tight-fitting mask."),
    ("HEPA air purifiers",
     "True HEPA filters capture at least 99.97% of 0.3-micron particles. "
     "Run the purifier in the room you use most, with doors closed, for "
     "at least 1–2 hours. A purifier only cleans the room it is in — it "
     "cannot clean a whole home at once."),
    ("Room size and CADR basics",
     "CADR (Clean Air Delivery Rate) says how much clean air a purifier "
     "delivers. As a rough guide, the CADR (in m³/h) should be at least "
     "2–3 times the room's volume in m³ per hour of cleaning — a bigger "
     "room needs a bigger purifier. Check the manufacturer's room-size "
     "rating before buying; an undersized purifier running on low will "
     "not keep up."),
    ("Filter replacement",
     "HEPA filters clog over time and lose effectiveness. Follow the "
     "manufacturer's replacement schedule (commonly 6–12 months, sooner "
     "in very dusty homes). A clogged filter can make the purifier noisier "
     "and less effective — check the indicator light and replace on time."),
]


@dataclass
class IndoorEstimate:
    """Result of the indoor PM2.5 estimate, with its inputs shown."""

    estimated_pm25: float
    outdoor_pm25: float
    ventilation: str
    ventilation_factor: float
    purifier_on: bool
    cooking: str
    cooking_addition: float
    risk_category: str = ""
    risk_advice: str = ""

    def summary(self) -> str:
        purifier_text = ("purifier running (about 55% removed)"
                         if self.purifier_on else "no purifier")
        return (
            f"Outdoor PM2.5 {self.outdoor_pm25:.1f} ug/m3 x "
            f"{self.ventilation_factor:.2f} ({self.ventilation.lower()}) + "
            f"{self.cooking_addition:.0f} from {self.cooking.lower()} = "
            f"about {self.estimated_pm25:.0f} ug/m3 indoors, {purifier_text}."
        )


def risk_category_for(pm25: float) -> tuple[str, str]:
    """Risk category + advice for an estimated indoor PM2.5 value."""
    for low, high, category, advice in RISK_BANDS:
        if low <= pm25 < high or (pm25 == low and low == 0.0):
            return category, advice
    return RISK_BANDS[-1][2], RISK_BANDS[-1][3]


def estimate_indoor_pm25(outdoor_pm25: float, ventilation: str,
                         purifier_on: bool, cooking: str,
                         room_size: str = "Medium (150–400 sq ft)",
                         occupants: int = 1,
                         cooking_frequency: str = "Once today",
                         smoking: bool = False) -> IndoorEstimate:
    """Estimate indoor PM2.5 from outdoor PM2.5 and room conditions.

    Model: indoor = (outdoor x ventilation_factor x purifier_factor
    + cooking_addition x frequency_factor + smoking + occupants)
    x room_size_factor. All parameters are documented above and shown in
    the UI. This is an estimate, not a measurement.
    """
    factor = VENTILATION_FACTORS.get(ventilation, 0.60)
    cooking_add = (COOKING_ADDITION.get(cooking, 0.0)
                   * COOKING_FREQUENCY_FACTORS.get(cooking_frequency, 1.0))
    base = float(outdoor_pm25) * factor
    if purifier_on:
        base *= (1.0 - PURIFIER_REDUCTION)
    extra = cooking_add
    if smoking:
        extra += SMOKING_ADDITION
    if occupants and occupants > 2:
        extra += (occupants - 2) * OCCUPANT_ADDITION
    room_factor = ROOM_SIZE_FACTORS.get(room_size, 1.0)
    total = round((base + extra) * room_factor, 1)
    category, advice = risk_category_for(total)
    return IndoorEstimate(
        estimated_pm25=total,
        outdoor_pm25=float(outdoor_pm25),
        ventilation=ventilation,
        ventilation_factor=factor,
        purifier_on=purifier_on,
        cooking=cooking,
        cooking_addition=round(cooking_add, 1),
        risk_category=category,
        risk_advice=advice,
    )


def improvement_comparison(outdoor_pm25: float, ventilation: str,
                           purifier_on: bool, cooking: str,
                           **kwargs) -> tuple[IndoorEstimate, IndoorEstimate, float]:
    """Before/after: current setup vs windows closed + purifier running.

    Returns (current estimate, improved estimate, percentage reduction).
    """
    current = estimate_indoor_pm25(outdoor_pm25, ventilation, purifier_on,
                                   cooking, **kwargs)
    improved = estimate_indoor_pm25(outdoor_pm25, "Windows closed", True,
                                    cooking, **kwargs)
    if current.estimated_pm25 <= 0:
        reduction = 0.0
    else:
        reduction = round(
            (current.estimated_pm25 - improved.estimated_pm25)
            / current.estimated_pm25 * 100.0, 1)
    return current, improved, max(reduction, 0.0)
