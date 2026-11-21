"""What If simulator: compare commute modes for the user's actual trip.

Shows estimated emissions (per day / week / month) and an exposure note
for each mode, with assumptions stated. Estimates, not measurements.
"""
from __future__ import annotations

from dataclasses import dataclass

from .alternatives import KG_CO2_PER_KM

# Exposure while travelling, by mode: (level, note)
EXPOSURE: dict[str, tuple[str, str]] = {
    "Metro": ("Low", "Mostly enclosed stations and coaches; short walks at each end."),
    "Bus": ("Medium", "Waiting at stops and open windows can raise exposure."),
    "Auto-rickshaw": ("Medium", "Open vehicle — roadside air reaches you directly."),
    "Two-wheeler": ("High", "You ride in traffic fumes; a mask helps a lot."),
    "Cycle": ("High", "Zero emissions, but hard breathing in roadside air."),
    "Walk": ("High", "Zero emissions, but you breathe roadside air directly."),
    "Car (petrol/diesel)": ("Low", "Closed windows + recirculation keep most particles out."),
    "Car (electric)": ("Low", "Closed windows + recirculation keep most particles out."),
    "Carpool": ("Low", "Closed windows + recirculation keep most particles out."),
    "Work from home": ("None", "No trip, no travel exposure at all."),
}

MODES = ["Metro", "Bus", "Auto-rickshaw", "Two-wheeler", "Cycle", "Walk",
         "Car (petrol/diesel)", "Car (electric)", "Carpool", "Work from home"]


@dataclass
class ModeComparison:
    """One mode's estimated emissions and exposure for the trip."""

    mode: str
    co2_per_day_kg: float
    co2_per_week_kg: float
    co2_per_month_kg: float
    exposure_level: str
    exposure_note: str
    saving_vs_current_kg_week: float = 0.0


def compare_modes(commute_km: float, current_mode: str,
                  days_per_week: int = 5) -> list[ModeComparison]:
    """Compare all modes for a return commute of `commute_km` each way."""
    km = max(commute_km, 0.0)
    days = max(days_per_week, 0)
    current_factor = KG_CO2_PER_KM.get(current_mode, 0.17)
    current_week = current_factor * km * 2 * days
    rows = []
    for mode in MODES:
        factor = KG_CO2_PER_KM.get(mode, 0.0)
        per_day = factor * km * 2
        per_week = per_day * days
        level, note = EXPOSURE.get(mode, ("Medium", ""))
        rows.append(ModeComparison(
            mode=mode,
            co2_per_day_kg=round(per_day, 2),
            co2_per_week_kg=round(per_week, 1),
            co2_per_month_kg=round(per_week * 4.33, 1),
            exposure_level=level,
            exposure_note=note,
            saving_vs_current_kg_week=round(current_week - per_week, 1),
        ))
    return rows


def lowest_emission_mode(rows: list[ModeComparison]) -> ModeComparison | None:
    """The lowest-emission mode (ties broken by lowest exposure)."""
    if not rows:
        return None
    order = {"None": 0, "Low": 1, "Medium": 2, "High": 3}
    return min(rows, key=lambda r: (r.co2_per_week_kg,
                                    order.get(r.exposure_level, 2)))


def lowest_exposure_mode(rows: list[ModeComparison]) -> ModeComparison | None:
    """The lowest-exposure motorised mode (excluding work from home)."""
    travelling = [r for r in rows if r.mode != "Work from home"]
    if not travelling:
        return None
    order = {"None": 0, "Low": 1, "Medium": 2, "High": 3}
    return min(travelling, key=lambda r: (order.get(r.exposure_level, 2),
                                          r.co2_per_week_kg))


# --- Time-of-day and cooking scenarios --------------------------------------


@dataclass
class TimeComparison:
    """Exposure comparison between two hours of the day."""

    hour_a: int
    hour_b: int
    aqi_a: float | None
    aqi_b: float | None
    pm25_a: float | None
    pm25_b: float | None
    recommendation: str


def compare_times(report, hour_a: int, hour_b: int) -> TimeComparison:
    """Compare the forecast air at two hours (e.g. 7 AM vs 6 PM)."""
    from .safety import hourly_aqi_at
    from .utils import hour_label

    def pm_at(hour: int) -> float | None:
        for point in report.today_hours():
            try:
                if int(point.time[11:13]) == hour:
                    return point.pm2_5
            except (ValueError, IndexError):
                continue
        return None

    aqi_a = hourly_aqi_at(report, hour_a)
    aqi_b = hourly_aqi_at(report, hour_b)
    if aqi_a is None or aqi_b is None:
        recommendation = ("No forecast is available for one of those hours "
                          "— check the hourly chart on the Home page.")
    elif aqi_a == aqi_b:
        recommendation = (f"Both hours are forecast at AQI {aqi_a:g} — "
                          "no difference today.")
    else:
        better, worse = (hour_a, hour_b) if aqi_a < aqi_b else (hour_b, hour_a)
        low, high = min(aqi_a, aqi_b), max(aqi_a, aqi_b)
        drop = round((high - low) / high * 100) if high > 0 else 0
        if drop == 0:
            recommendation = (
                f"Both hours are forecast at nearly the same AQI "
                f"({low:g} vs {high:g}) — no meaningful difference today.")
        else:
            recommendation = (
                f"{hour_label(better)} is better than {hour_label(worse)}: "
                f"AQI {low:g} vs {high:g} — about {drop}% lower. The same "
                "activity at the cleaner hour means lower particulate exposure.")
    return TimeComparison(hour_a=hour_a, hour_b=hour_b, aqi_a=aqi_a,
                          aqi_b=aqi_b, pm25_a=pm_at(hour_a),
                          pm25_b=pm_at(hour_b),
                          recommendation=recommendation)


@dataclass
class CookingComparison:
    """Indoor PM2.5 with vs without chimney use while cooking."""

    outdoor_pm25: float
    with_chimney_pm25: float
    without_chimney_pm25: float
    reduction_pct: float
    note: str


def cooking_ventilation_scenario(outdoor_pm25: float) -> CookingComparison:
    """Estimate cooking-time indoor PM2.5 with and without a chimney.

    Assumption (disclosed): a working chimney extracts cooking smoke at
    the source, modelled as no cooking contribution indoors; without a
    chimney, gas cooking twice today adds its full contribution. Both
    use the same indoor estimator.
    """
    from .indoor import estimate_indoor_pm25
    with_chimney = estimate_indoor_pm25(
        outdoor_pm25, "Windows cracked / trickle vent", False,
        "No cooking right now")
    without = estimate_indoor_pm25(
        outdoor_pm25, "Windows cracked / trickle vent", False,
        "Gas cooking", cooking_frequency="Twice today")
    reduction = 0.0
    if without.estimated_pm25 > 0:
        reduction = round((without.estimated_pm25
                           - with_chimney.estimated_pm25)
                          / without.estimated_pm25 * 100, 1)
    return CookingComparison(
        outdoor_pm25=outdoor_pm25,
        with_chimney_pm25=with_chimney.estimated_pm25,
        without_chimney_pm25=without.estimated_pm25,
        reduction_pct=reduction,
        note=("Estimate only: a working chimney is modelled as removing "
              "the cooking contribution. Real results depend on the "
              "chimney's power, the room, and what is cooked."))
