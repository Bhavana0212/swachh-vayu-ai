"""Forecast intelligence: pollution predictor, anomaly detection, seasons.

All rule-based on the Open-Meteo forecast — labelled "forecast-based
outlook, not a trained prediction model". Nothing here invents data:
spikes come from the 5-day trend, anomalies from the recent 24-hour
mean, and seasonal notes are educational patterns for India.
"""
from __future__ import annotations

from dataclasses import dataclass

from .api import AirReport
from .indian_aqi import category_for as indian_category_for
from .utils import hour_label

PREDICTOR_NOTE = ("Forecast-based outlook from the 5-day modelled forecast — "
                  "not a trained prediction model.")


@dataclass
class Spike:
    """A forecast pollution spike: a day much worse than the day before."""

    day: str
    aqi: float
    previous_aqi: float
    rise_pct: float
    category: str
    advice: str


def detect_spikes(report: AirReport, threshold_pct: float = 20.0,
                  ) -> list[Spike]:
    """Days in the 5-day forecast where max AQI jumps vs the previous day.

    Uses the indicative Indian AQI per day when available, else US AQI.
    """
    trend = report.daily_trend()
    spikes: list[Spike] = []
    prev: float | None = None
    for day, us_max, _pm, indian_max in trend:
        value = indian_max if indian_max is not None else us_max
        if value is None:
            prev = None
            continue
        if prev is not None and prev > 0:
            rise = (value - prev) / prev * 100
            if rise >= threshold_pct:
                category = indian_category_for(value)[0]
                spikes.append(Spike(
                    day=day, aqi=value, previous_aqi=prev,
                    rise_pct=round(rise, 1), category=category,
                    advice=(f"Pollution is forecast to rise about "
                            f"{rise:.0f}% on {day} (AQI {value:g}, "
                            f"{category}). Plan outdoor time for earlier in "
                            "the week, keep the purifier ready, and check "
                            "the day's plan that morning."),
                ))
        prev = value
    return spikes


@dataclass
class Anomaly:
    """An unusual change vs the recent trend, in plain language."""

    title: str
    message: str
    direction: str  # "up" | "down"


def detect_anomalies(report: AirReport) -> list[Anomaly]:
    """Compare current PM2.5 / AQI with the recent 24-hour mean.

    A change of 50% or more is flagged as unusual. No data -> no anomaly.
    """
    anomalies: list[Anomaly] = []
    current = report.current
    hourly = report.hourly
    if not hourly or current.time is None:
        return anomalies
    pm_values = [p.pm2_5 for p in hourly
                 if p.pm2_5 is not None and p.time < current.time]
    if current.pm2_5 is not None and len(pm_values) >= 6:
        mean_pm = sum(pm_values) / len(pm_values)
        if mean_pm > 0:
            change = (current.pm2_5 - mean_pm) / mean_pm * 100
            if change >= 50:
                anomalies.append(Anomaly(
                    title="PM2.5 has jumped sharply",
                    message=(f"PM2.5 is {current.pm2_5:.0f} µg/m³ now, "
                             f"about {change:.0f}% above the recent 24-hour "
                             f"average of {mean_pm:.0f} µg/m³. This can "
                             "happen with a weather change, local burning, "
                             "or dust — check the hourly trend below."),
                    direction="up"))
            elif change <= -50:
                anomalies.append(Anomaly(
                    title="PM2.5 has dropped sharply",
                    message=(f"PM2.5 is {current.pm2_5:.0f} µg/m³ now, "
                             f"about {abs(change):.0f}% below the recent "
                             f"24-hour average of {mean_pm:.0f} µg/m³ — "
                             "often after rain or stronger wind."),
                    direction="down"))
    return anomalies


# Educational seasonal patterns for India (general knowledge, not a
# forecast). Month ranges are approximate and vary by region.
SEASONS: dict[str, dict[str, str]] = {
    "winter": {
        "months": "December – February",
        "pattern": ("Worst season for most of North India: cold air traps "
                    "pollution near the ground (inversion), stubble burning "
                    "adds smoke in October–November, and Diwali fireworks "
                    "spike PM2.5 for days."),
        "advice": ("Plan outdoor time for late morning, when the inversion "
                   "lifts a little; keep windows closed on smog mornings."),
    },
    "summer": {
        "months": "March – June",
        "pattern": ("Dust storms and dry winds raise PM10; ozone rises with "
                    "strong sunlight. Heat waves add a second health risk "
                    "on top of the air."),
        "advice": ("Avoid midday outdoor exercise in peak heat; dust masks "
                   "help on windy days."),
    },
    "monsoon": {
        "months": "July – September",
        "pattern": ("Cleanest season: rain washes particles out of the air "
                    "and strong winds disperse pollution. Humidity is high, "
                    "which can make breathing feel harder."),
        "advice": ("The best season for outdoor routines — but watch for "
                   "mould and damp indoors after heavy rain."),
    },
    "post_monsoon": {
        "months": "October – November",
        "pattern": ("Air quality worsens fast as the monsoon ends: stubble "
                    "burning in Punjab/Haryana, calm winds, and Diwali "
                    "fireworks combine into the year's worst weeks."),
        "advice": ("Keep the purifier ready, stock N95 masks, and check the "
                   "forecast daily — conditions change fast."),
    },
}


def season_for_month(month: int) -> str:
    """Season key for a calendar month (1-12)."""
    if month in (12, 1, 2):
        return "winter"
    if month in (3, 4, 5, 6):
        return "summer"
    if month in (7, 8, 9):
        return "monsoon"
    return "post_monsoon"


def seasonal_analysis(report: AirReport, month: int) -> dict[str, str]:
    """Seasonal context for the current month + what the forecast says."""
    key = season_for_month(month)
    info = SEASONS[key]
    aqi, scale, category = report.primary_aqi()
    trend = report.daily_trend()
    worst_day = None
    if trend:
        ranked = [(d, (i if i is not None else u))
                  for d, u, _pm, i in trend if (i if i is not None else u)]
        if ranked:
            worst_day = max(ranked, key=lambda item: item[1])
    return {
        "season": key.replace("_", " ").title(),
        "months": info["months"],
        "pattern": info["pattern"],
        "advice": info["advice"],
        "today": (f"Today's {scale} is {aqi:g} ({category}) in "
                  f"{report.city.name}."
                  if aqi is not None else
                  "No current reading is available."),
        "forecast_note": (
            f"The worst day in the 5-day forecast is {worst_day[0]} "
            f"(AQI {worst_day[1]:g})." if worst_day else
            "No 5-day forecast is available right now."),
    }


def morning_briefing(report: AirReport, profile) -> dict[str, str]:
    """Smart Morning Briefing: morning AQI + weather + suggested routine.

    `profile` is a planner.routine.Profile (duck-typed to avoid a cycle).
    """
    from .routine import build_day_plan
    aqi, scale, category = report.primary_aqi()
    weather = report.weather
    best = report.best_hour_today()
    worst = report.worst_hour_today()
    plan = build_day_plan(profile, report)
    weather_bits = []
    if weather.temperature_c is not None:
        weather_bits.append(f"{weather.temperature_c:.0f}°C")
    if weather.humidity_pct is not None:
        weather_bits.append(f"humidity {weather.humidity_pct:.0f}%")
    if weather.wind_kmh is not None:
        weather_bits.append(
            f"wind {weather.wind_kmh:.0f} km/h {weather.wind_compass()}")
    weather_line = ", ".join(weather_bits) if weather_bits else \
        "Weather data unavailable"
    timing = ""
    if best is not None and best.primary_aqi is not None:
        timing = (f"Cleanest hour today: {hour_label(best.time)} "
                  f"(AQI {best.primary_aqi:g}).")
    if worst is not None and worst.primary_aqi is not None:
        timing += (f" Worst hour: {hour_label(worst.time)} "
                   f"(AQI {worst.primary_aqi:g}).")
    top_items = [item.title for item in plan.items[:3]]
    return {
        "headline": (f"{scale} {aqi:g} ({category}) in {report.city.name}"
                     if aqi is not None else
                     "No current AQI reading — check again shortly."),
        "weather": weather_line,
        "timing": timing.strip(),
        "routine": " · ".join(top_items),
        "plan_headline": plan.headline,
    }
