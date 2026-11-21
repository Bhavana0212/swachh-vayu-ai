"""Clean Air Digital Twin (EXPERIMENTAL).

An educational simulation, NOT a scientific prediction: the user changes
city-level scenario sliders and sees how a simple, fully disclosed model
moves the current AQI. Every output is labelled as a simulation, and the
model's assumptions are shown next to the result.
"""
from __future__ import annotations

from dataclasses import dataclass

from .api import AirReport
from .indian_aqi import category_for as indian_category_for

TWIN_LABEL = ("EDUCATIONAL SIMULATION — not a scientific prediction. "
              "The model below is a simple teaching tool with disclosed "
              "assumptions; real city air quality depends on weather, "
              "sources and chemistry this model does not capture.")

# Model weights (disclosed): how much each scenario lever moves the AQI
# at its maximum setting. Traffic and household emissions push AQI up;
# green cover and metro shift pull it down.
SCENARIOS = {
    "traffic": {
        "label": "Traffic volume",
        "range": (-30, 30),
        "unit": "%",
        "weight": 0.6,
        "note": ("Traffic is a major urban NO2 and PM source; the model "
                 "moves AQI by 0.6 points per 1% traffic change."),
    },
    "green_cover": {
        "label": "Green cover / urban vegetation",
        "range": (0, 30),
        "unit": "% more",
        "weight": -0.4,
        "note": ("Trees trap some dust and cool streets, but they cannot "
                 "fix city-wide smog alone; the model moves AQI by 0.4 "
                 "points per 1% more green cover."),
    },
    "household": {
        "label": "Household emissions (cooking, waste burning)",
        "range": (-30, 30),
        "unit": "%",
        "weight": 0.5,
        "note": ("Cooking smoke and open waste burning add PM2.5; the model "
                 "moves AQI by 0.5 points per 1% change."),
    },
    "metro_shift": {
        "label": "Metro / bus shift (trips moved from cars)",
        "range": (0, 40),
        "unit": "% of trips",
        "weight": -0.5,
        "note": ("Every car trip moved to metro or bus removes one "
                 "vehicle's exhaust; the model moves AQI by 0.5 points "
                 "per 1% of trips shifted."),
    },
}


@dataclass
class TwinResult:
    """One simulated scenario."""

    base_aqi: float
    simulated_aqi: int
    base_category: str
    simulated_category: str
    delta: int
    changes: dict[str, float]
    explanation: str


def simulate(report: AirReport, traffic: float = 0.0,
             green_cover: float = 0.0, household: float = 0.0,
             metro_shift: float = 0.0) -> TwinResult | None:
    """Run the educational simulation from the current primary AQI."""
    aqi, _scale, _category = report.primary_aqi()
    if aqi is None:
        return None
    changes = {"traffic": traffic, "green_cover": green_cover,
               "household": household, "metro_shift": metro_shift}
    delta = round(
        traffic * SCENARIOS["traffic"]["weight"]
        + green_cover * SCENARIOS["green_cover"]["weight"]
        + household * SCENARIOS["household"]["weight"]
        + metro_shift * SCENARIOS["metro_shift"]["weight"])
    simulated = max(0, min(500, round(aqi + delta)))
    base_cat = indian_category_for(aqi)[0]
    sim_cat = indian_category_for(simulated)[0]
    if delta < 0:
        direction = (f"about {abs(delta)} points cleaner — from "
                     f"{base_cat} to {sim_cat}." if base_cat != sim_cat else
                     f"about {abs(delta)} points cleaner, still {base_cat}.")
    elif delta > 0:
        direction = (f"about {delta} points worse — from {base_cat} to "
                     f"{sim_cat}." if base_cat != sim_cat else
                     f"about {delta} points worse, still {base_cat}.")
    else:
        direction = "unchanged — the levers cancel out or are at zero."
    return TwinResult(
        base_aqi=aqi, simulated_aqi=simulated, base_category=base_cat,
        simulated_category=sim_cat, delta=delta, changes=changes,
        explanation=(f"In this simulation the city's AQI moves from "
                     f"{aqi:g} to {simulated} — {direction} Remember: this "
                     "is a teaching model with simple weights, not a "
                     "scientific forecast."),
    )


def improvement_suggestions(result: TwinResult) -> list[str]:
    """Plain-language suggestions from a simulation result."""
    suggestions = []
    changes = result.changes
    if changes["metro_shift"] > 0:
        suggestions.append(
            "Shifting trips to metro/bus is the strongest lever in this "
            "model — it removes vehicle exhaust at the source.")
    if changes["green_cover"] > 0:
        suggestions.append(
            "Green cover helps modestly here — trees trap dust and cool "
            "streets, but they work best alongside emission cuts.")
    if changes["household"] < 0:
        suggestions.append(
            "Cutting household emissions (cleaner cooking, no waste "
            "burning) improves the air closest to where people live.")
    if changes["traffic"] > 0:
        suggestions.append(
            "More traffic makes the simulation worse — the model shows why "
            "congestion days feel worse to breathe.")
    if not suggestions:
        suggestions.append(
            "Move a slider to see how each lever changes the city's air — "
            "then compare which change matters most.")
    return suggestions
