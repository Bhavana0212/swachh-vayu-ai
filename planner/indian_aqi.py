"""Calculated Indian AQI — CPCB methodology, computed in-app.

Source: CPCB official "About National Air Quality Index" (cpcb.gov.in),
verified 20 Nov 2026. The breakpoint table below uses those numbers
EXACTLY — no invented breakpoints.

Method:
* Sub-index per pollutant = linear interpolation within its breakpoint band.
* Overall AQI = the WORST (maximum) sub-index, capped at 500.
* 24-hour means for PM2.5 / PM10 / NO2 / SO2; 8-hour means for O3 / CO.
* Open-Meteo CO is in ug/m3 -> divide by 1000 to mg/m3 BEFORE breakpoints.
* CPCB rule: minimum 3 pollutants, one of which must be PM2.5 or PM10.
  Otherwise NO calculated Indian AQI is shown ("insufficient data").
* NH3 and Pb are NOT available from Open-Meteo -> "not available", never
  invented.

The Severe band has no upper bound in the CPCB table. Convention used
here (documented, using only table numbers): the Severe band is
interpolated over the previous band's width and the result is capped at
500. Example: PM2.5 Severe = 250–379 ug/m3 -> AQI 401–500; above 379 the
index is 500.

Interpolation runs through the table's PUBLISHED integer edge points
(e.g. PM2.5 Satisfactory is 31–60 ug/m3 -> AQI 51–100), which reproduces
CPCB's own worked example exactly: PM2.5 31 -> 51, 45 -> 75, 60 -> 100.
Fractional concentrations between two published edges (e.g. 30.5) are
interpolated linearly between the neighbouring edge points.

This is a CALCULATED AQI from modelled concentrations — labelled
"Calculated Indian AQI (CPCB method) from modelled data — not a CPCB
station reading" wherever it appears.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

# CPCB categories: (low, high, category, colour, text colour, symbol)
CATEGORIES: list[tuple[int, int, str, str, str, str]] = [
    (0, 50, "Good", "#00B050", "#1A1A1A", "✓"),
    (51, 100, "Satisfactory", "#92D050", "#1A1A1A", "○"),
    (101, 200, "Moderately polluted", "#FFFF00", "#1A1A1A", "△"),
    (201, 300, "Poor", "#FF9900", "#1A1A1A", "▲"),
    (301, 400, "Very Poor", "#FF0000", "#FFFFFF", "◆"),
    (401, 500, "Severe", "#C00000", "#FFFFFF", "■"),
]

# CPCB breakpoints, EXACT from the verified table. Each band is
# (conc_low, conc_high, aqi_low, aqi_high) with the table's PUBLISHED
# integer edges (e.g. PM2.5 Satisfactory is 31–60, NOT 30–60 — CPCB's own
# worked example, PM2.5 31 -> 51, 45 -> 75, 60 -> 100, only holds with
# these edges). sub_index() interpolates through the edge points.
# PM2.5/PM10/NO2/SO2/NH3/Pb: 24-hr mean, ug/m3. O3: 8-hr mean, ug/m3.
# CO: 8-hr mean, mg/m3. (CO Poor starts at 10.1 per the +0.1 pattern of
# the CO column and secondary CPCB reproductions; the CPCB PDF prints
# "10-17" there.)
BREAKPOINTS: dict[str, list[tuple[float, float, int, int]]] = {
    "pm2_5": [
        (0.0, 30.0, 0, 50), (31.0, 60.0, 51, 100),
        (61.0, 90.0, 101, 200), (91.0, 120.0, 201, 300),
        (121.0, 250.0, 301, 400),
    ],
    "pm10": [
        (0.0, 50.0, 0, 50), (51.0, 100.0, 51, 100),
        (101.0, 250.0, 101, 200), (251.0, 350.0, 201, 300),
        (351.0, 430.0, 301, 400),
    ],
    "nitrogen_dioxide": [
        (0.0, 40.0, 0, 50), (41.0, 80.0, 51, 100),
        (81.0, 180.0, 101, 200), (181.0, 280.0, 201, 300),
        (281.0, 400.0, 301, 400),
    ],
    "ozone": [
        (0.0, 50.0, 0, 50), (51.0, 100.0, 51, 100),
        (101.0, 168.0, 101, 200), (169.0, 208.0, 201, 300),
        (209.0, 748.0, 301, 400),
    ],
    "carbon_monoxide": [  # mg/m3
        (0.0, 1.0, 0, 50), (1.1, 2.0, 51, 100),
        (2.1, 10.0, 101, 200), (10.1, 17.0, 201, 300),
        (17.1, 34.0, 301, 400),
    ],
    "sulphur_dioxide": [
        (0.0, 40.0, 0, 50), (41.0, 80.0, 51, 100),
        (81.0, 380.0, 101, 200), (381.0, 800.0, 201, 300),
        (801.0, 1600.0, 301, 400),
    ],
    "nh3": [
        (0.0, 200.0, 0, 50), (201.0, 400.0, 51, 100),
        (401.0, 800.0, 101, 200), (801.0, 1200.0, 201, 300),
        (1201.0, 1800.0, 301, 400),
    ],
    "pb": [
        (0.0, 0.5, 0, 50), (0.5, 1.0, 51, 100),
        (1.1, 2.0, 101, 200), (2.1, 3.0, 201, 300),
        (3.1, 3.5, 301, 400),
    ],
}

# Severe-band low per pollutant (the "250+" etc. from the table).
SEVERE_LOW: dict[str, float] = {
    "pm2_5": 250.0, "pm10": 430.0, "nitrogen_dioxide": 400.0,
    "ozone": 748.0, "carbon_monoxide": 34.0, "sulphur_dioxide": 1600.0,
    "nh3": 1800.0, "pb": 3.5,
}

# Averaging windows (hours) per pollutant.
AVERAGING_HOURS: dict[str, int] = {
    "pm2_5": 24, "pm10": 24, "nitrogen_dioxide": 24, "sulphur_dioxide": 24,
    "ozone": 8, "carbon_monoxide": 8,
}

# Pollutants Open-Meteo provides (NH3 and Pb are NOT available).
AVAILABLE_POLLUTANTS = ("pm2_5", "pm10", "nitrogen_dioxide",
                        "sulphur_dioxide", "carbon_monoxide", "ozone")
UNAVAILABLE_POLLUTANTS = ("nh3", "pb")

LABEL = ("Calculated Indian AQI (CPCB method) from modelled data — "
         "not a CPCB station reading")


def category_for(aqi: float | None) -> tuple[str, str, str, str]:
    """(category, colour, text colour, symbol) for an AQI value."""
    if aqi is None:
        return "Unavailable", "#E5E7EB", "#1A1A1A", "?"
    for low, high, category, colour, text, symbol in CATEGORIES:
        if low <= aqi <= high:
            return category, colour, text, symbol
    return CATEGORIES[-1][2], CATEGORIES[-1][3], CATEGORIES[-1][4], \
        CATEGORIES[-1][5]


def _edge_points(pollutant: str) -> list[tuple[float, float]]:
    """Ordered (concentration, AQI) edge points for one pollutant.

    Built from the published band edges, e.g. PM2.5 gives
    (0,0), (30,50), (31,51), (60,100), (61,101), ... (250,400).
    """
    points: list[tuple[float, float]] = []
    for conc_low, conc_high, aqi_low, aqi_high in BREAKPOINTS[pollutant]:
        points.append((float(conc_low), float(aqi_low)))
        points.append((float(conc_high), float(aqi_high)))
    points.sort()
    return points


def sub_index(pollutant: str, concentration: float | None) -> int | None:
    """CPCB sub-index for one pollutant at one averaged concentration.

    Returns None for a missing concentration or unknown pollutant.
    Concentrations: ug/m3, except CO in mg/m3. Interpolation runs
    through the table's published edge points, so CPCB's worked example
    holds exactly (PM2.5 31 -> 51, 45 -> 75, 60 -> 100); fractional
    concentrations between two published edges interpolate across the
    gap. The Severe band is interpolated over the previous band's width
    and capped at 500.
    """
    if concentration is None:
        return None
    table = BREAKPOINTS.get(pollutant)
    if table is None:
        return None
    conc = float(concentration)
    if conc <= 0:
        return 0
    points = _edge_points(pollutant)
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x1 == x0:
            continue  # zero-width step (Pb shares 0.5); skip it
        if x0 <= conc <= x1:
            frac = (conc - x0) / (x1 - x0)
            return round(y0 + frac * (y1 - y0))
    # Above the last closed band: Severe band, interpolated over the
    # previous band's width, capped at 500.
    last_low, last_high, _, _ = table[-1]
    width = last_high - last_low
    severe_low = SEVERE_LOW[pollutant]
    if conc >= severe_low + width:
        return 500
    frac = (conc - severe_low) / width
    return round(401 + frac * (500 - 401))


def mean_over(values: list[tuple[str, float | None]], end: datetime,
              hours: int) -> tuple[float | None, int]:
    """Mean of values in the `hours` hours ending at `end` (inclusive).

    Returns (mean, count). Values with missing data are skipped; when no
    values exist the mean is None.
    """
    start = end - timedelta(hours=hours - 1)
    collected = []
    for time_iso, value in values:
        if value is None:
            continue
        try:
            ts = datetime.fromisoformat(time_iso)
        except ValueError:
            continue
        if start <= ts <= end:
            collected.append(float(value))
    if not collected:
        return None, 0
    return round(sum(collected) / len(collected), 2), len(collected)


@dataclass
class IndianAQI:
    """Result of the in-app Indian AQI calculation."""

    value: int | None
    category: str
    colour: str
    text_colour: str
    symbol: str
    dominant: str  # pollutant key, or "none"
    sub_indices: dict[str, int] = field(default_factory=dict)
    means: dict[str, float] = field(default_factory=dict)
    hours_used: dict[str, int] = field(default_factory=dict)
    available: bool = True
    reason: str = ""
    basis: str = ""

    def badge_html(self) -> str:
        """Accessible badge: colour + text + symbol, never colour alone."""
        if self.value is None:
            return (
                '<span role="img" aria-label="Indian AQI unavailable" '
                'style="background:#E5E7EB;color:#1A1A1A;padding:2px 10px;'
                'border-radius:999px;font-weight:700;">? Indian AQI — '
                'unavailable</span>'
            )
        return (
            f'<span role="img" aria-label="Calculated Indian AQI '
            f'{self.value}, {self.category}" style="background:{self.colour};'
            f"color:{self.text_colour};padding:2px 10px;border-radius:999px;"
            f'font-weight:700;font-size:0.95rem;">{self.symbol} Indian AQI '
            f"{self.value} — {self.category}</span>"
        )


def calculate_indian_aqi(
        hourly: dict[str, list[tuple[str, float | None]]],
        current_time: str) -> IndianAQI:
    """Calculate the Indian AQI from hourly modelled concentrations.

    `hourly` maps pollutant key -> [(ISO time, value)] with CO in ug/m3
    (converted to mg/m3 here). `current_time` is the ISO data time of the
    latest reading. Returns an IndianAQI with available=False when the
    CPCB minimum (3 pollutants incl. PM2.5 or PM10) is not met.
    """
    try:
        end = datetime.fromisoformat(current_time)
    except ValueError:
        end = datetime.now()
    means: dict[str, float] = {}
    hours_used: dict[str, int] = {}
    for pollutant in AVAILABLE_POLLUTANTS:
        values = hourly.get(pollutant, [])
        if pollutant == "carbon_monoxide":
            values = [(t, (v / 1000.0 if v is not None else None))
                      for t, v in values]
        mean, count = mean_over(values, end, AVERAGING_HOURS[pollutant])
        if mean is not None:
            means[pollutant] = mean
            hours_used[pollutant] = count
    has_pm = "pm2_5" in means or "pm10" in means
    if len(means) < 3 or not has_pm:
        return IndianAQI(
            value=None, category="Unavailable", colour="#E5E7EB",
            text_colour="#1A1A1A", symbol="?", dominant="none",
            sub_indices={}, means=means, hours_used=hours_used,
            available=False,
            reason=("Insufficient data for Indian AQI: need at least 3 "
                    "pollutants including PM2.5 or PM10; got "
                    f"{len(means)} ({', '.join(sorted(means)) or 'none'})."),
            basis="",
        )
    sub_indices: dict[str, int] = {}
    for pollutant, mean in means.items():
        sub = sub_index(pollutant, mean)
        if sub is not None:
            sub_indices[pollutant] = sub
    dominant = max(sub_indices, key=lambda k: sub_indices[k])
    value = min(sub_indices[dominant], 500)
    category, colour, text, symbol = category_for(value)
    partial = [p for p, n in hours_used.items()
               if n < AVERAGING_HOURS[p]]
    if partial:
        basis = ("Partial means: " + ", ".join(
            f"{p} {hours_used[p]}h of {AVERAGING_HOURS[p]}h"
            for p in sorted(partial)))
    else:
        basis = ("24-hr means (PM2.5, PM10, NO2, SO2), 8-hr means (O3, CO); "
                 "full windows available")
    return IndianAQI(
        value=value, category=category, colour=colour, text_colour=text,
        symbol=symbol, dominant=dominant, sub_indices=sub_indices,
        means=means, hours_used=hours_used, available=True,
        reason="", basis=basis,
    )


def indian_aqi_from_single_hour(values: dict[str, float | None]) -> IndianAQI:
    """Indicative Indian AQI from ONE hour's concentrations.

    Used for hourly/activity views where no averaging window exists. The
    single-hour values stand in for the means, so the result is an
    INDICATIVE estimate, not a CPCB-compliant AQI — the UI labels it so.
    """
    means: dict[str, float] = {}
    for pollutant in AVAILABLE_POLLUTANTS:
        value = values.get(pollutant)
        if value is None:
            continue
        means[pollutant] = value / 1000.0 if pollutant == "carbon_monoxide" \
            else float(value)
    has_pm = "pm2_5" in means or "pm10" in means
    if len(means) < 3 or not has_pm:
        return IndianAQI(
            value=None, category="Unavailable", colour="#E5E7EB",
            text_colour="#1A1A1A", symbol="?", dominant="none",
            available=False,
            reason="Insufficient data for an indicative Indian AQI.",
            basis="Single-hour indicative estimate",
        )
    sub_indices = {p: sub_index(p, m) for p, m in means.items()}
    sub_indices = {p: s for p, s in sub_indices.items() if s is not None}
    dominant = max(sub_indices, key=lambda k: sub_indices[k])
    value = min(sub_indices[dominant], 500)
    category, colour, text, symbol = category_for(value)
    return IndianAQI(
        value=value, category=category, colour=colour, text_colour=text,
        symbol=symbol, dominant=dominant, sub_indices=sub_indices,
        means=means, hours_used={p: 1 for p in means}, available=True,
        reason="", basis="Single-hour indicative estimate",
    )
