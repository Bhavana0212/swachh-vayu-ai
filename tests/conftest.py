"""Shared fixtures: a realistic Open-Meteo response and derived objects."""
import pytest

from planner.api import AirReport, City, parse_air_quality
from planner.routine import Profile


@pytest.fixture
def delhi_city():
    return City(name="Delhi", country="India", latitude=28.65,
                longitude=77.23, timezone="Asia/Kolkata")


@pytest.fixture
def api_response():
    """Realistic Air Quality API payload: current + 48 hourly points."""
    hours = []
    aqis = []
    pm25 = []
    pm10 = []
    no2 = []
    so2 = []
    co = []
    o3 = []
    eu_aqi = []
    dust = []
    # Day 1: morning peak, clean afternoon. Day 2: flat moderate.
    day1_aqi = [180, 175, 170, 165, 160, 165, 190, 220, 235, 225, 200, 180,
                160, 140, 125, 120, 130, 150, 180, 205, 215, 210, 200, 190]
    day2_aqi = [110] * 24
    for day, values in (("2026-11-21", day1_aqi), ("2026-11-22", day2_aqi)):
        for hour, aqi in enumerate(values):
            hours.append(f"{day}T{hour:02d}:00")
            aqis.append(aqi)
            pm25.append(round(aqi * 0.6, 1))
            pm10.append(round(aqi * 0.9, 1))
            no2.append(round(30 + aqi * 0.1, 1))
            so2.append(round(10 + aqi * 0.08, 1))
            co.append(round(800 + aqi * 6.0, 1))
            o3.append(round(60 - aqi * 0.1, 1))
            eu_aqi.append(round(aqi * 0.45))
            dust.append(round(1 + aqi * 0.02, 1))
    return {
        "latitude": 28.6,
        "longitude": 77.2,
        "timezone": "Asia/Kolkata",
        "current": {
            "time": "2026-11-21T08:30",
            "us_aqi": 219,
            "european_aqi": 100,
            "pm2_5": 139.2,
            "pm10": 140.2,
            "nitrogen_dioxide": 51.1,
            "ozone": 42.0,
            "sulphur_dioxide": 43.5,
            "carbon_monoxide": 2126.0,
            "dust": 1.0,
        },
        "hourly": {
            "time": hours,
            "us_aqi": aqis,
            "european_aqi": eu_aqi,
            "pm2_5": pm25,
            "pm10": pm10,
            "nitrogen_dioxide": no2,
            "sulphur_dioxide": so2,
            "carbon_monoxide": co,
            "ozone": o3,
            "dust": dust,
        },
    }


@pytest.fixture
def report(delhi_city, api_response):
    return parse_air_quality(api_response, delhi_city)


@pytest.fixture
def profile():
    return Profile(sensitivity="General", commute_mode="Metro",
                   commute_km=10.0, exercises_outdoors=True,
                   exercise_minutes=30, has_purifier=False)


@pytest.fixture
def sensitive_profile():
    return Profile(sensitivity="Asthma / respiratory condition",
                   commute_mode="Cycle", commute_km=6.0,
                   exercises_outdoors=True, exercise_minutes=45,
                   has_purifier=True)
