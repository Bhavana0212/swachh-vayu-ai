"""AQI banding, colours, health guidance and pollutant sub-indices.

Two scales are supported:

* US AQI (EPA): 0-500, six bands. Colours are the official EPA palette.
* European AQI (EEA): 0-100+, six bands. Colours follow the EEA palette.

Sub-indices use the US EPA breakpoint tables. They are computed from the
CURRENT hourly concentration, so they are indicative only — a regulatory
AQI uses 24-hour (particles) or 8-hour (ozone, CO) averages. The app says
so wherever a sub-index is shown.
"""
from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# US AQI bands (EPA): (low, high, category, background colour, text colour)
# ---------------------------------------------------------------------------
US_BANDS: list[tuple[int, int, str, str, str]] = [
    (0, 50, "Good", "#00E400", "#1A1A1A"),
    (51, 100, "Moderate", "#FFFF00", "#1A1A1A"),
    (101, 150, "Unhealthy for Sensitive Groups", "#FF7E00", "#1A1A1A"),
    (151, 200, "Unhealthy", "#FF0000", "#FFFFFF"),
    (201, 300, "Very Unhealthy", "#8F3F97", "#FFFFFF"),
    (301, 500, "Hazardous", "#7E0023", "#FFFFFF"),
]

# European AQI bands (EEA): (low, high, category, background colour, text)
EU_BANDS: list[tuple[int, int, str, str, str]] = [
    (0, 20, "Good", "#50F0E6", "#1A1A1A"),
    (21, 40, "Fair", "#50CCAA", "#1A1A1A"),
    (41, 60, "Moderate", "#F0E641", "#1A1A1A"),
    (61, 80, "Poor", "#FF5050", "#FFFFFF"),
    (81, 100, "Very Poor", "#960032", "#FFFFFF"),
    (101, 1000, "Extremely Poor", "#7D2181", "#FFFFFF"),
]

# Indian CPCB / NAQI bands, for EXPLANATION ONLY (Learn page). The app does
# NOT compute or display an Indian NAQI value — primary numbers are always
# the API's US / European AQI. (low, high, category, colour)
NAQI_BANDS: list[tuple[int, int, str, str]] = [
    (0, 50, "Good", "#00B050"),
    (51, 100, "Satisfactory", "#92D050"),
    (101, 200, "Moderate", "#FFFF00"),
    (201, 300, "Poor", "#FF9900"),
    (301, 400, "Very Poor", "#FF0000"),
    (401, 500, "Severe", "#C00000"),
]

# Colour-independent symbols, one per US band: AQI is never conveyed by
# colour alone (Accessibility Mode requirement).
BAND_SYMBOLS: dict[str, str] = {
    "Good": "✓",
    "Moderate": "○",
    "Unhealthy for Sensitive Groups": "△",
    "Unhealthy": "▲",
    "Very Unhealthy": "◆",
    "Hazardous": "■",
    "Unavailable": "?",
}

# General health guidance per US band, and extra guidance for sensitive
# people. This is general public-health information, not medical advice.
US_GUIDANCE: dict[str, str] = {
    "Good": "Air quality is good. Enjoy outdoor activities as usual.",
    "Moderate": "Air quality is acceptable. Unusually sensitive people should "
    "consider shortening long or heavy outdoor exertion.",
    "Unhealthy for Sensitive Groups": "Sensitive groups may feel health "
    "effects. They should shorten or move long outdoor exertion indoors; "
    "everyone else can carry on as usual.",
    "Unhealthy": "Everyone may begin to feel health effects. Sensitive groups "
    "should avoid long or heavy outdoor exertion; others should shorten it.",
    "Very Unhealthy": "Health alert: the risk of health effects is higher for "
    "everyone. Avoid long or heavy outdoor exertion; keep windows closed.",
    "Hazardous": "Health warning of emergency conditions. Avoid all outdoor "
    "exertion; stay indoors with windows closed and air cleaned if possible.",
}

SENSITIVE_EXTRA: dict[str, str] = {
    "Good": "No special precautions needed today.",
    "Moderate": "If you have asthma or a heart or lung condition, keep your "
    "reliever handy and take it easier than usual outdoors.",
    "Unhealthy for Sensitive Groups": "Asthma, heart or lung conditions, "
    "children and older adults: move long outdoor activity indoors and wear a "
    "well-fitting N95/FFP2 mask if you must be outside.",
    "Unhealthy": "Sensitive groups should stay indoors as much as possible and "
    "wear a well-fitting N95/FFP2 mask for any essential trip outside.",
    "Very Unhealthy": "Sensitive groups should stay indoors, keep windows "
    "closed, run a purifier if available, and seek care promptly if symptoms "
    "worsen.",
    "Hazardous": "Everyone, especially sensitive groups, should remain indoors "
    "with windows closed. Seek medical advice if you feel unwell.",
}

# EPA sub-index breakpoints: pollutant -> [(conc_low, conc_high, aqi_low,
# aqi_high)] for PM2.5/PM10 (24h), O3 (8h), NO2 (1h), SO2 (1h), CO (8h).
# Concentrations in ug/m3, except CO in mg/m3.
BREAKPOINTS: dict[str, list[tuple[float, float, int, int]]] = {
    "pm2_5": [
        (0.0, 12.0, 0, 50), (12.1, 35.4, 51, 100), (35.5, 55.4, 101, 150),
        (55.5, 150.4, 151, 200), (150.5, 250.4, 201, 300), (250.5, 500.4, 301, 500),
    ],
    "pm10": [
        (0.0, 54.0, 0, 50), (55.0, 154.0, 51, 100), (155.0, 254.0, 101, 150),
        (255.0, 354.0, 151, 200), (355.0, 424.0, 201, 300), (425.0, 604.0, 301, 500),
    ],
    "ozone": [
        (0.0, 108.0, 0, 50), (109.0, 140.0, 51, 100), (141.0, 165.0, 101, 150),
        (166.0, 204.0, 151, 200), (205.0, 404.0, 201, 300), (405.0, 604.0, 301, 500),
    ],
    "nitrogen_dioxide": [
        (0.0, 100.0, 0, 50), (101.0, 188.0, 51, 100), (189.0, 677.0, 101, 150),
        (678.0, 1221.0, 151, 200), (1222.0, 2349.0, 201, 300),
        (2350.0, 3853.0, 301, 500),
    ],
    "sulphur_dioxide": [
        (0.0, 92.0, 0, 50), (93.0, 196.0, 51, 100), (197.0, 484.0, 101, 150),
        (485.0, 796.0, 151, 200), (797.0, 1582.0, 201, 300),
        (1583.0, 2629.0, 301, 500),
    ],
    # CO is handled in mg/m3: EPA uses ppm; 1 ppm CO ~ 1.145 mg/m3.
    "carbon_monoxide": [
        (0.0, 5.1, 0, 50), (5.2, 10.8, 51, 100), (10.9, 14.3, 101, 150),
        (14.4, 17.3, 151, 200), (17.4, 34.5, 201, 300), (34.6, 57.5, 301, 500),
    ],
}

POLLUTANT_LABELS: dict[str, str] = {
    "pm2_5": "PM2.5 (fine particles)",
    "pm10": "PM10 (coarse particles)",
    "nitrogen_dioxide": "NO2 (nitrogen dioxide)",
    "ozone": "Ozone (O3)",
    "sulphur_dioxide": "SO2 (sulphur dioxide)",
    "carbon_monoxide": "CO (carbon monoxide)",
    "dust": "Dust",
}

# Short, plain-language health notes per pollutant.
POLLUTANT_EFFECTS: dict[str, str] = {
    "pm2_5": "Tiny particles that reach deep into the lungs and bloodstream; "
    "linked to asthma attacks, heart and lung strain, and long-term risk.",
    "pm10": "Coarser dust and particles that irritate eyes, nose and airways; "
    "worse near roads, construction and dry, dusty ground.",
    "nitrogen_dioxide": "Traffic and combustion fumes; irritates airways and "
    "worsens asthma, especially near busy roads.",
    "ozone": "Forms in sunlight from traffic fumes; irritates lungs and eyes "
    "and peaks on warm, sunny afternoons.",
    "sulphur_dioxide": "Burning fossil fuels and industry; irritates the "
    "throat and lungs, particularly for people with asthma.",
    "carbon_monoxide": "Vehicle exhaust and incomplete burning; reduces "
    "oxygen delivery in the blood; dangerous in enclosed spaces.",
    "dust": "Wind-blown desert and soil dust; irritates eyes and airways.",
}


@dataclass(frozen=True)
class Band:
    """One AQI band: category, colours and guidance."""

    category: str
    colour: str
    text_colour: str
    guidance: str

    def badge_html(self, value: int | float, label: str = "AQI") -> str:
        """Accessible badge: colour + text + symbol, never colour alone.

        Background and text colours are paired for contrast, the category
        is written out in words, a distinct symbol marks the band, and an
        aria-label gives screen readers the full meaning.
        """
        symbol = BAND_SYMBOLS.get(self.category, "?")
        return (
            f'<span role="img" aria-label="{label} {value:g}, '
            f'{self.category}" style="background:{self.colour};'
            f"color:{self.text_colour};padding:2px 10px;border-radius:999px;"
            f'font-weight:700;font-size:0.95rem;">{symbol} {label} {value:g} '
            f"— {self.category}</span>"
        )


def _band_for(value: float, bands) -> tuple[str, str, str]:
    for low, high, category, colour, text in bands:
        if low <= value <= high:
            return category, colour, text
    last = bands[-1]
    return last[2], last[3], last[4]


def us_band(aqi: float | None) -> Band:
    """US AQI band for a value, or an 'unavailable' band for None."""
    if aqi is None:
        return Band("Unavailable", "#E5E7EB", "#1A1A1A",
                    "No AQI value available right now.")
    category, colour, text = _band_for(float(aqi), US_BANDS)
    return Band(category, colour, text, US_GUIDANCE[category])


def eu_band(aqi: float | None) -> Band:
    """European AQI band for a value, or an 'unavailable' band for None."""
    if aqi is None:
        return Band("Unavailable", "#E5E7EB", "#1A1A1A",
                    "No AQI value available right now.")
    category, colour, text = _band_for(float(aqi), EU_BANDS)
    return Band(category, colour, text, US_GUIDANCE.get(
        category, "Check the US AQI guidance for the equivalent band."))


def sub_index(pollutant: str, concentration: float | None) -> int | None:
    """EPA sub-index for one pollutant at one concentration (indicative).

    Returns None when the concentration is missing. Values above the top
    breakpoint are capped at 500; values below the first band start at 0.
    CO concentrations are expected in mg/m3; all others in ug/m3.
    """
    if concentration is None:
        return None
    table = BREAKPOINTS.get(pollutant)
    if table is None:
        return None
    conc = float(concentration)
    if conc <= 0:
        return 0
    for conc_low, conc_high, aqi_low, aqi_high in table:
        if conc_low <= conc <= conc_high:
            if conc_high == conc_low:
                return aqi_low
            frac = (conc - conc_low) / (conc_high - conc_low)
            return round(aqi_low + frac * (aqi_high - aqi_low))
    if conc > table[-1][1]:
        return 500
    return 0


def dominant_pollutant(concentrations: dict[str, float | None]) -> tuple[str, int | None]:
    """Return (pollutant key, sub-index) of the highest sub-index.

    CO is converted from ug/m3 (as returned by the API) to mg/m3 first.
    Returns ("none", None) when no pollutant has a value.
    """
    best_key = "none"
    best_value: int | None = None
    for key, value in concentrations.items():
        if value is None or key not in BREAKPOINTS:
            continue
        conc = value / 1000.0 if key == "carbon_monoxide" else value
        sub = sub_index(key, conc)
        if sub is not None and (best_value is None or sub > best_value):
            best_key, best_value = key, sub
    return best_key, best_value


def sensitive_guidance(category: str) -> str:
    """Extra guidance for sensitive groups for a US band category."""
    return SENSITIVE_EXTRA.get(
        category, "Take the usual precautions for your condition.")


def aqi_difference_pct(from_aqi: float, to_aqi: float) -> float:
    """Percentage change from one AQI to another (negative = cleaner)."""
    if from_aqi <= 0:
        return 0.0
    return round((to_aqi - from_aqi) / from_aqi * 100.0, 1)
