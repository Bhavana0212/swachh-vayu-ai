"""Open-Meteo data layer (free, no API key) — INDIA ONLY.

SwachhVayu AI covers Indian cities only. Geocoding results are filtered
to country_code == "IN"; a non-Indian search gets a clear note instead
of results.

Sources (all free, non-commercial, no key):
* Air Quality API — https://air-quality-api.open-meteo.com/v1/air-quality
  (Copernicus CAMS modelled data; current + hourly, past_hours=24 for the
  CPCB averaging windows + 5-day forecast, timezone Asia/Kolkata)
* Geocoding API — https://geocoding-api.open-meteo.com/v1/search
* Forecast API — https://api.open-meteo.com/v1/forecast (weather context)

Honesty rule: the air-quality values are MODELLED (CAMS) values, not
ground-station measurements. The Indian AQI shown is CALCULATED in-app
from those modelled concentrations using the CPCB methodology — never a
CPCB station reading. When the network is unavailable the app falls back
to clearly labelled SAMPLE data and shows a banner.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from .indian_aqi import (
    IndianAQI,
    calculate_indian_aqi,
    indian_aqi_from_single_hour,
)

AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT_SECONDS = 12
TIMEZONE = "Asia/Kolkata"
IST = ZoneInfo(TIMEZONE)

DATA_SOURCE = ("Latest available modelled estimate — Open-Meteo Air Quality "
               "API (Copernicus CAMS modelled data)")
DATA_NOTE = (
    "Latest available modelled estimate from Copernicus CAMS via Open-Meteo — "
    "NOT live sensor data and not a ground-station measurement. The Indian "
    "AQI is calculated in-app from these modelled concentrations (CPCB "
    "method) — it is not a CPCB station reading. Values can differ from "
    "local monitors."
)
INDIA_ONLY_NOTE = "SwachhVayu AI covers India only."


def ist_now() -> datetime:
    """Current date/time in IST (Asia/Kolkata)."""
    return datetime.now(IST)


# Quick cities (10, India only): name -> (latitude, longitude, country)
QUICK_CITIES: dict[str, tuple[float, float, str]] = {
    "Delhi": (28.65, 77.23, "India"),
    "Mumbai": (19.07, 72.88, "India"),
    "Bengaluru": (12.97, 77.59, "India"),
    "Kolkata": (22.56, 88.36, "India"),
    "Chennai": (13.09, 80.28, "India"),
    "Hyderabad": (17.38, 78.46, "India"),
    "Pune": (18.52, 73.86, "India"),
    "Lucknow": (26.84, 80.92, "India"),
    "Patna": (25.59, 85.14, "India"),
    "Jaipur": (26.92, 75.79, "India"),
}

# Demo cities: one representative use-case each (see README / Learn).
DEMO_CITIES: dict[str, str] = {
    "Delhi": "High-pollution scenario, protective daily routine",
    "Mumbai": "Coastal urban environment, humidity, transport choices",
    "Bengaluru": "Tech city, metro and two-wheeler commute",
    "Kolkata": "Eastern India, winter smog",
}

# Bundled Indian city database: state -> [(name, latitude, longitude)]
# Coordinates verified against the Open-Meteo Geocoding API at build
# time (20 Nov 2026); each entry is the most populous IN match.
INDIAN_CITIES: dict[str, list[tuple[str, float, float]]] = {
    "Assam": [("Guwahati", 26.18, 91.75)],
    "Bihar": [("Gaya", 24.8, 85.0), ("Patna", 25.59, 85.14)],
    "Chandigarh": [("Chandigarh", 30.74, 76.79)],
    "Chhattisgarh": [("Raipur", 21.23, 81.63)],
    "Delhi": [("Delhi", 28.65, 77.23)],
    "Gujarat": [("Ahmedabad", 23.03, 72.59), ("Rajkot", 22.29, 70.79),
                ("Surat", 21.2, 72.83), ("Vadodara", 22.3, 73.21)],
    "Haryana": [("Faridabad", 28.41, 77.31), ("Gurugram", 28.46, 77.03),
                ("Kurukshetra", 29.97, 76.84)],
    "Himachal Pradesh": [("Shimla", 31.1, 77.17)],
    "Jammu and Kashmir": [("Srinagar", 34.09, 74.81)],
    "Jharkhand": [("Ranchi", 23.34, 85.31)],
    "Karnataka": [("Bengaluru", 12.97, 77.59), ("Mysuru", 12.3, 76.64)],
    "Kerala": [("Kochi", 9.94, 76.26), ("Thiruvananthapuram", 8.49, 76.95)],
    "Madhya Pradesh": [("Bhopal", 23.25, 77.4), ("Indore", 22.72, 75.83)],
    "Maharashtra": [("Mumbai", 19.07, 72.88), ("Nagpur", 21.15, 79.08),
                    ("Pune", 18.52, 73.86)],
    "Odisha": [("Bhubaneswar", 20.27, 85.83)],
    "Punjab": [("Amritsar", 31.62, 74.88), ("Ludhiana", 30.91, 75.85)],
    "Rajasthan": [("Jaipur", 26.92, 75.79), ("Jodhpur", 26.27, 73.01),
                  ("Udaipur", 24.59, 73.71)],
    "Tamil Nadu": [("Chennai", 13.09, 80.28), ("Coimbatore", 11.01, 76.97),
                   ("Madurai", 9.92, 78.12)],
    "Telangana": [("Hyderabad", 17.38, 78.46), ("Warangal", 18.0, 79.58)],
    "Uttar Pradesh": [("Agra", 27.18, 78.02), ("Ghaziabad", 28.67, 77.44),
                      ("Kanpur", 26.47, 80.35), ("Lucknow", 26.84, 80.92),
                      ("Noida", 28.58, 77.33), ("Varanasi", 25.32, 83.01)],
    "Uttarakhand": [("Dehradun", 30.32, 78.03)],
    "West Bengal": [("Howrah", 22.58, 88.32), ("Kolkata", 22.56, 88.36)],
}

# Clearly-labelled sample values, used ONLY when the live API is
# unreachable. They are typical winter values for each city, not measurements.
SAMPLE_CURRENT: dict[str, dict[str, float]] = {
    "Delhi": {"us_aqi": 312, "european_aqi": 100, "pm2_5": 210.0, "pm10": 320.0,
              "nitrogen_dioxide": 58.0, "ozone": 28.0, "sulphur_dioxide": 22.0,
              "carbon_monoxide": 1400.0, "dust": 12.0},
    "Mumbai": {"us_aqi": 168, "european_aqi": 78, "pm2_5": 88.0, "pm10": 150.0,
               "nitrogen_dioxide": 42.0, "ozone": 45.0, "sulphur_dioxide": 18.0,
               "carbon_monoxide": 900.0, "dust": 9.0},
    "Bengaluru": {"us_aqi": 128, "european_aqi": 58, "pm2_5": 46.0, "pm10": 92.0,
                  "nitrogen_dioxide": 28.0, "ozone": 52.0, "sulphur_dioxide": 9.0,
                  "carbon_monoxide": 700.0, "dust": 6.0},
    "Jaipur": {"us_aqi": 155, "european_aqi": 72, "pm2_5": 72.0, "pm10": 138.0,
               "nitrogen_dioxide": 33.0, "ozone": 48.0, "sulphur_dioxide": 11.0,
               "carbon_monoxide": 800.0, "dust": 18.0},
    "Kolkata": {"us_aqi": 178, "european_aqi": 82, "pm2_5": 98.0, "pm10": 165.0,
                "nitrogen_dioxide": 45.0, "ozone": 38.0, "sulphur_dioxide": 16.0,
                "carbon_monoxide": 1000.0, "dust": 10.0},
    "Chennai": {"us_aqi": 112, "european_aqi": 52, "pm2_5": 38.0, "pm10": 72.0,
                "nitrogen_dioxide": 25.0, "ozone": 55.0, "sulphur_dioxide": 12.0,
                "carbon_monoxide": 650.0, "dust": 8.0},
    "Hyderabad": {"us_aqi": 135, "european_aqi": 62, "pm2_5": 52.0, "pm10": 98.0,
                  "nitrogen_dioxide": 30.0, "ozone": 50.0, "sulphur_dioxide": 10.0,
                  "carbon_monoxide": 750.0, "dust": 9.0},
    "Pune": {"us_aqi": 118, "european_aqi": 55, "pm2_5": 42.0, "pm10": 82.0,
             "nitrogen_dioxide": 27.0, "ozone": 52.0, "sulphur_dioxide": 8.0,
             "carbon_monoxide": 700.0, "dust": 11.0},
    "Lucknow": {"us_aqi": 198, "european_aqi": 88, "pm2_5": 118.0, "pm10": 195.0,
                "nitrogen_dioxide": 48.0, "ozone": 35.0, "sulphur_dioxide": 15.0,
                "carbon_monoxide": 1100.0, "dust": 20.0},
    "Ahmedabad": {"us_aqi": 142, "european_aqi": 65, "pm2_5": 58.0, "pm10": 112.0,
                  "nitrogen_dioxide": 32.0, "ozone": 46.0, "sulphur_dioxide": 12.0,
                  "carbon_monoxide": 850.0, "dust": 22.0},
    "Patna": {"us_aqi": 205, "european_aqi": 90, "pm2_5": 128.0, "pm10": 210.0,
              "nitrogen_dioxide": 50.0, "ozone": 32.0, "sulphur_dioxide": 17.0,
              "carbon_monoxide": 1200.0, "dust": 24.0},
}
DEFAULT_SAMPLE = SAMPLE_CURRENT["Delhi"]

CURRENT_VARS = (
    "us_aqi,european_aqi,pm2_5,pm10,nitrogen_dioxide,ozone,"
    "sulphur_dioxide,carbon_monoxide,dust"
)
# Full hourly set: needed for the CPCB 24-hr/8-hr averaging windows.
HOURLY_VARS = (
    "pm2_5,pm10,nitrogen_dioxide,sulphur_dioxide,carbon_monoxide,ozone,"
    "us_aqi,european_aqi,dust"
)
HOURLY_POLLUTANTS = ("pm2_5", "pm10", "nitrogen_dioxide",
                     "sulphur_dioxide", "carbon_monoxide", "ozone")


@dataclass
class City:
    """A place the user asked about (India only)."""

    name: str
    country: str = "India"
    latitude: float = 0.0
    longitude: float = 0.0
    timezone: str = TIMEZONE
    admin1: str = ""


@dataclass
class CurrentAir:
    """Current air-quality reading for a city."""

    time: str
    us_aqi: float | None = None
    european_aqi: float | None = None
    pm2_5: float | None = None
    pm10: float | None = None
    nitrogen_dioxide: float | None = None
    ozone: float | None = None
    sulphur_dioxide: float | None = None
    carbon_monoxide: float | None = None
    dust: float | None = None

    def concentrations(self) -> dict[str, float | None]:
        """Pollutant concentrations (ug/m3) for sub-index maths."""
        return {
            "pm2_5": self.pm2_5,
            "pm10": self.pm10,
            "nitrogen_dioxide": self.nitrogen_dioxide,
            "ozone": self.ozone,
            "sulphur_dioxide": self.sulphur_dioxide,
            "carbon_monoxide": self.carbon_monoxide,
        }


@dataclass
class HourlyPoint:
    """One forecast hour, with all modelled pollutants."""

    time: str
    us_aqi: float | None = None
    european_aqi: float | None = None
    pm2_5: float | None = None
    pm10: float | None = None
    nitrogen_dioxide: float | None = None
    ozone: float | None = None
    sulphur_dioxide: float | None = None
    carbon_monoxide: float | None = None
    dust: float | None = None
    indian_aqi: int | None = None  # indicative single-hour estimate

    @property
    def primary_aqi(self) -> float | None:
        """Best AQI for this hour: indicative Indian AQI, else US AQI."""
        return self.indian_aqi if self.indian_aqi is not None else self.us_aqi

    def concentrations(self) -> dict[str, float | None]:
        return {
            "pm2_5": self.pm2_5,
            "pm10": self.pm10,
            "nitrogen_dioxide": self.nitrogen_dioxide,
            "ozone": self.ozone,
            "sulphur_dioxide": self.sulphur_dioxide,
            "carbon_monoxide": self.carbon_monoxide,
        }


@dataclass
class WeatherNow:
    """Current weather context for a city."""

    time: str = ""
    temperature_c: float | None = None
    humidity_pct: float | None = None
    wind_kmh: float | None = None
    wind_direction_deg: float | None = None
    weather_code: int | None = None
    precipitation_mm: float | None = None

    def wind_compass(self) -> str:
        """Wind direction as a compass label (N, NE, ...)."""
        if self.wind_direction_deg is None:
            return "—"
        labels = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        idx = round(self.wind_direction_deg / 45) % 8
        return labels[idx]


WEATHER_CODE_LABELS: dict[int, str] = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog", 51: "Light drizzle",
    53: "Moderate drizzle", 55: "Dense drizzle", 56: "Light freezing drizzle",
    57: "Dense freezing drizzle", 61: "Slight rain", 63: "Moderate rain",
    65: "Heavy rain", 66: "Light freezing rain", 67: "Heavy freezing rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    77: "Snow grains", 80: "Slight rain showers", 81: "Moderate rain showers",
    82: "Violent rain showers", 85: "Slight snow showers",
    86: "Heavy snow showers", 95: "Thunderstorm",
    96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
}


def _unavailable_indian_aqi() -> IndianAQI:
    return IndianAQI(
        value=None, category="Unavailable", colour="#E5E7EB",
        text_colour="#1A1A1A", symbol="?", dominant="none",
        available=False, reason="No hourly data available.",
        basis="")


@dataclass
class AirReport:
    """Everything the dashboard needs for one city."""

    city: City
    current: CurrentAir
    hourly: list[HourlyPoint] = field(default_factory=list)
    weather: WeatherNow = field(default_factory=WeatherNow)
    is_live: bool = True
    fetched_at: str = ""
    source: str = DATA_SOURCE
    indian_aqi: IndianAQI = field(default_factory=_unavailable_indian_aqi)

    # -- primary AQI -------------------------------------------------------
    def primary_aqi(self) -> tuple[float | None, str, str]:
        """(value, scale label, category) — calculated Indian AQI first.

        Falls back to US AQI (labelled) when the Indian AQI cannot be
        calculated.
        """
        if self.indian_aqi.available and self.indian_aqi.value is not None:
            return (float(self.indian_aqi.value), "Indian AQI (CPCB)",
                    self.indian_aqi.category)
        if self.current.us_aqi is not None:
            from .aqi import us_band
            band = us_band(self.current.us_aqi)
            return float(self.current.us_aqi), "US AQI", band.category
        return None, "Indian AQI (CPCB)", "Unavailable"

    def data_confidence(self) -> dict[str, str]:
        """Per-value data status: 'modelled' / 'estimated' / 'missing'.

        'modelled' = Open-Meteo CAMS value; 'estimated' = calculated in-app
        from modelled data; 'missing' = not available; 'sample' = offline
        fallback values (whole report, when is_live is False).
        """
        if not self.is_live:
            return {key: "sample" for key in (
                "indian_aqi", "us_aqi", "european_aqi", "pm2_5", "pm10",
                "nitrogen_dioxide", "ozone", "sulphur_dioxide",
                "carbon_monoxide", "dust", "weather")}
        status: dict[str, str] = {}
        status["indian_aqi"] = ("estimated" if self.indian_aqi.available
                                else "missing")
        for key in ("us_aqi", "european_aqi", "pm2_5", "pm10",
                    "nitrogen_dioxide", "ozone", "sulphur_dioxide",
                    "carbon_monoxide", "dust"):
            status[key] = ("modelled"
                           if getattr(self.current, key) is not None
                           else "missing")
        status["weather"] = ("modelled"
                             if self.weather.temperature_c is not None
                             else "missing")
        return status

    # -- derived views -----------------------------------------------------
    def today_hours(self) -> list[HourlyPoint]:
        """Hourly points for the calendar day of the current reading."""
        if not self.current.time:
            return self.hourly[:24]
        day = self.current.time[:10]
        today = [p for p in self.hourly if p.time.startswith(day)]
        return today or self.hourly[:24]

    def best_hour_today(self) -> HourlyPoint | None:
        """Lowest-primary-AQI hour today (None when no hourly data)."""
        points = [p for p in self.today_hours() if p.primary_aqi is not None]
        return min(points, key=lambda p: p.primary_aqi) if points else None

    def worst_hour_today(self) -> HourlyPoint | None:
        """Highest-primary-AQI hour today (None when no hourly data)."""
        points = [p for p in self.today_hours() if p.primary_aqi is not None]
        return max(points, key=lambda p: p.primary_aqi) if points else None

    def cleanest_window(self, hours: int = 3) -> tuple[str, str, float] | None:
        """Lowest average primary-AQI window of `hours` consecutive hours.

        Returns (start time, end time, average AQI) or None.
        """
        points = [p for p in self.today_hours() if p.primary_aqi is not None]
        if len(points) < hours:
            return None
        best_start, best_avg = 0, float("inf")
        for i in range(len(points) - hours + 1):
            avg = sum(p.primary_aqi for p in points[i:i + hours]) / hours
            if avg < best_avg:
                best_start, best_avg = i, avg
        start = points[best_start].time
        end = points[best_start + hours - 1].time
        return start, end, round(best_avg, 1)

    def daily_trend(self) -> list[tuple[str, float | None, float | None,
                                        float | None]]:
        """Per-day (date, max US AQI, mean PM2.5, max Indian AQI).

        Only days from today onwards (forecast), up to 5 days.
        """
        by_day: dict[str, list[HourlyPoint]] = {}
        today = self.current.time[:10] if self.current.time else ""
        for point in self.hourly:
            if today and point.time[:10] < today:
                continue
            by_day.setdefault(point.time[:10], []).append(point)
        trend = []
        for day in sorted(by_day):
            points = by_day[day]
            aqis = [p.us_aqi for p in points if p.us_aqi is not None]
            pms = [p.pm2_5 for p in points if p.pm2_5 is not None]
            ind = [p.indian_aqi for p in points
                   if p.indian_aqi is not None]
            trend.append((
                day,
                max(aqis) if aqis else None,
                round(sum(pms) / len(pms), 1) if pms else None,
                max(ind) if ind else None,
            ))
        return trend[:5]


class ApiError(RuntimeError):
    """Raised when an Open-Meteo request fails or returns bad data."""


def _get_json(url: str, params: dict) -> dict:
    try:
        response = requests.get(url, params=params, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ApiError(f"Open-Meteo request failed: {exc}") from exc
    try:
        data = response.json()
    except ValueError as exc:
        raise ApiError("Open-Meteo returned invalid JSON.") from exc
    if not isinstance(data, dict):
        raise ApiError("Open-Meteo returned an unexpected response.")
    return data


def search_cities(query: str, count: int = 5) -> list[City]:
    """Geocode an Indian city name. Returns [] for blank queries or no
    Indian matches. Results are filtered to country_code == 'IN'."""
    cities, _ = search_cities_with_note(query, count)
    return cities


def search_cities_with_note(query: str, count: int = 5,
                            ) -> tuple[list[City], bool]:
    """Geocode a city name, India only.

    Returns (indian cities, had_non_indian_results). The caller shows
    INDIA_ONLY_NOTE when the second value is True and no Indian city
    matched.
    """
    query = (query or "").strip()
    if not query:
        return [], False
    data = _get_json(GEOCODING_URL, {
        "name": query, "count": max(1, min(count, 10)),
        "language": "en", "format": "json",
    })
    cities: list[City] = []
    had_non_indian = False
    for item in data.get("results", []) or []:
        if item.get("country_code") != "IN":
            had_non_indian = True
            continue
        cities.append(City(
            name=item.get("name", query),
            country=item.get("country", "India"),
            latitude=float(item["latitude"]),
            longitude=float(item["longitude"]),
            timezone=TIMEZONE,
            admin1=item.get("admin1", ""),
        ))
    return cities, had_non_indian


def city_from_bundled(name: str) -> City | None:
    """Look up a bundled Indian city by name (state database)."""
    for state, entries in INDIAN_CITIES.items():
        for city_name, lat, lon in entries:
            if city_name.lower() == name.lower():
                return City(name=city_name, latitude=lat, longitude=lon,
                            admin1=state)
    return None


def parse_air_quality(data: dict, city: City) -> AirReport:
    """Parse an Air Quality API response into an AirReport (no network).

    Also calculates the Indian AQI from the hourly concentrations and an
    indicative Indian AQI for every hourly point.
    """
    current = data.get("current") or {}
    hourly = data.get("hourly") or {}
    times = hourly.get("time") or []

    def series(key: str) -> list:
        return hourly.get(key) or []

    columns = {key: series(key) for key in HOURLY_POLLUTANTS}
    columns["us_aqi"] = series("us_aqi")
    columns["european_aqi"] = series("european_aqi")
    columns["dust"] = series("dust")

    points = []
    for i, t in enumerate(times):
        values = {key: (col[i] if i < len(col) else None)
                  for key, col in columns.items()}
        indicative = indian_aqi_from_single_hour(
            {k: values[k] for k in HOURLY_POLLUTANTS})
        points.append(HourlyPoint(
            time=t,
            us_aqi=values["us_aqi"],
            european_aqi=values["european_aqi"],
            pm2_5=values["pm2_5"],
            pm10=values["pm10"],
            nitrogen_dioxide=values["nitrogen_dioxide"],
            ozone=values["ozone"],
            sulphur_dioxide=values["sulphur_dioxide"],
            carbon_monoxide=values["carbon_monoxide"],
            dust=values["dust"],
            indian_aqi=(indicative.value if indicative.available else None),
        ))

    current_time = current.get("time", "")
    hourly_by_pollutant = {
        key: [(times[i], (columns[key][i] if i < len(columns[key]) else None))
              for i in range(len(times))]
        for key in HOURLY_POLLUTANTS
    }
    indian = (calculate_indian_aqi(hourly_by_pollutant, current_time)
              if current_time else _unavailable_indian_aqi())

    return AirReport(
        city=city,
        current=CurrentAir(
            time=current_time,
            us_aqi=current.get("us_aqi"),
            european_aqi=current.get("european_aqi"),
            pm2_5=current.get("pm2_5"),
            pm10=current.get("pm10"),
            nitrogen_dioxide=current.get("nitrogen_dioxide"),
            ozone=current.get("ozone"),
            sulphur_dioxide=current.get("sulphur_dioxide"),
            carbon_monoxide=current.get("carbon_monoxide"),
            dust=current.get("dust"),
        ),
        hourly=points,
        is_live=True,
        fetched_at=ist_now().isoformat(timespec="minutes"),
        indian_aqi=indian,
    )


def fetch_air(city: City) -> AirReport:
    """Fetch live air quality + weather for a city. Raises ApiError."""
    data = _get_json(AIR_QUALITY_URL, {
        "latitude": city.latitude, "longitude": city.longitude,
        "current": CURRENT_VARS, "hourly": HOURLY_VARS,
        "past_hours": 24, "forecast_days": 5, "timezone": TIMEZONE,
    })
    report = parse_air_quality(data, city)
    try:
        weather = _get_json(FORECAST_URL, {
            "latitude": city.latitude, "longitude": city.longitude,
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,"
                       "wind_direction_10m,weather_code,precipitation",
            "timezone": TIMEZONE,
        })
        current = weather.get("current") or {}
        report.weather = WeatherNow(
            time=current.get("time", ""),
            temperature_c=current.get("temperature_2m"),
            humidity_pct=current.get("relative_humidity_2m"),
            wind_kmh=current.get("wind_speed_10m"),
            wind_direction_deg=current.get("wind_direction_10m"),
            weather_code=current.get("weather_code"),
            precipitation_mm=current.get("precipitation"),
        )
    except ApiError:
        # Weather is context only; a failed weather call must not kill the
        # air-quality report.
        report.weather = WeatherNow()
    return report


def fetch_past_days(city: City, days: int = 7,
                    ) -> list[tuple[str, float | None, float | None]]:
    """Historical daily values: (date, max US AQI, mean PM2.5).

    Uses the Air Quality API's past_days parameter. Returns [] on failure
    (the caller falls back to locally stored snapshots).
    """
    try:
        data = _get_json(AIR_QUALITY_URL, {
            "latitude": city.latitude, "longitude": city.longitude,
            "hourly": "pm2_5,us_aqi",
            "past_days": max(1, min(days, 30)), "forecast_days": 1,
            "timezone": TIMEZONE,
        })
    except ApiError:
        return []
    hourly = data.get("hourly") or {}
    times = hourly.get("time") or []
    aqis = hourly.get("us_aqi") or []
    pm25 = hourly.get("pm2_5") or []
    by_day: dict[str, dict[str, list[float]]] = {}
    for i, t in enumerate(times):
        day = t[:10]
        bucket = by_day.setdefault(day, {"aqi": [], "pm": []})
        if i < len(aqis) and aqis[i] is not None:
            bucket["aqi"].append(aqis[i])
        if i < len(pm25) and pm25[i] is not None:
            bucket["pm"].append(pm25[i])
    out = []
    for day in sorted(by_day):
        bucket = by_day[day]
        out.append((
            day,
            max(bucket["aqi"]) if bucket["aqi"] else None,
            round(sum(bucket["pm"]) / len(bucket["pm"]), 1)
            if bucket["pm"] else None,
        ))
    return out


def sample_report(city: City) -> AirReport:
    """Clearly-labelled sample report for offline use.

    Built from typical values for the city (or Delhi's when unknown) with
    a synthetic 24-hour curve for every pollutant, so the calculated
    Indian AQI also works on sample data. is_live=False marks it.
    """
    sample = SAMPLE_CURRENT.get(city.name, DEFAULT_SAMPLE)
    now = ist_now()
    day = now.strftime("%Y-%m-%d")
    base_aqi = float(sample["us_aqi"])
    # Synthetic diurnal shape: worst at 8 AM and 8 PM, cleanest mid-afternoon.
    shape = [1.05, 1.02, 1.0, 0.98, 0.96, 0.98, 1.05, 1.12, 1.18, 1.12, 1.05,
             0.98, 0.92, 0.88, 0.85, 0.86, 0.9, 0.98, 1.08, 1.15, 1.12, 1.08,
             1.06, 1.05]
    points = []
    for hour, factor in enumerate(shape):
        values = {key: round(float(sample[key]) * factor, 1)
                  for key in ("pm2_5", "pm10", "nitrogen_dioxide", "ozone",
                              "sulphur_dioxide", "carbon_monoxide", "dust")}
        indicative = indian_aqi_from_single_hour(values)
        points.append(HourlyPoint(
            time=f"{day}T{hour:02d}:00",
            us_aqi=round(base_aqi * factor),
            european_aqi=round(float(sample["european_aqi"]) * factor),
            indian_aqi=(indicative.value if indicative.available else None),
            **values,
        ))
    current_time = f"{day}T{now.hour:02d}:00"
    hourly_by_pollutant = {
        key: [(p.time, getattr(p, key)) for p in points]
        for key in HOURLY_POLLUTANTS
    }
    indian = calculate_indian_aqi(hourly_by_pollutant, current_time)
    return AirReport(
        city=city,
        current=CurrentAir(time=current_time, **{
            key: sample[key] for key in (
                "us_aqi", "european_aqi", "pm2_5", "pm10",
                "nitrogen_dioxide", "ozone", "sulphur_dioxide",
                "carbon_monoxide", "dust")}),
        hourly=points,
        is_live=False,
        fetched_at=now.isoformat(timespec="minutes"),
        source="SAMPLE DATA — live data unavailable",
        indian_aqi=indian,
    )


def quick_city(name: str) -> City:
    """City object for a quick-city name (raises KeyError when unknown)."""
    lat, lon, country = QUICK_CITIES[name]
    return City(name=name, country=country, latitude=lat, longitude=lon)
