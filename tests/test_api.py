"""API parsing, derived views, mocked network calls, sample fallback."""
from unittest.mock import patch

import pytest
import requests

from planner import api as api_module
from planner.api import (
    ApiError,
    City,
    fetch_air,
    parse_air_quality,
    quick_city,
    sample_report,
    search_cities,
)


def test_parse_current_values(report):
    assert report.current.us_aqi == 219
    assert report.current.european_aqi == 100
    assert report.current.pm2_5 == 139.2
    assert report.current.carbon_monoxide == 2126.0
    assert report.current.time == "2026-11-21T08:30"


def test_parse_hourly_length(report):
    assert len(report.hourly) == 48
    assert report.hourly[0].time == "2026-11-21T00:00"
    assert report.hourly[8].us_aqi == 235


def test_parse_is_live_and_source(report):
    assert report.is_live is True
    assert "Open-Meteo" in report.source


def test_parse_handles_missing_sections(delhi_city):
    parsed = parse_air_quality({}, delhi_city)
    assert parsed.current.us_aqi is None
    assert parsed.hourly == []
    assert parsed.best_hour_today() is None


def test_parse_handles_short_hourly_arrays(delhi_city):
    parsed = parse_air_quality({
        "current": {"time": "2026-11-21T08:00", "us_aqi": 120},
        "hourly": {"time": ["2026-11-21T08:00"], "us_aqi": [120]},
    }, delhi_city)
    assert len(parsed.hourly) == 1
    assert parsed.hourly[0].pm2_5 is None


def test_today_hours_filters_to_current_day(report):
    today = report.today_hours()
    assert len(today) == 24
    assert all(p.time.startswith("2026-11-21") for p in today)


def test_best_and_worst_hour_today(report):
    best = report.best_hour_today()
    worst = report.worst_hour_today()
    assert best.time == "2026-11-21T15:00"  # AQI 120, the day's low
    assert best.us_aqi == 120
    assert worst.time == "2026-11-21T08:00"  # AQI 235, the day's high
    assert worst.us_aqi == 235


def test_cleanest_window_three_hours(report):
    window = report.cleanest_window(3)
    assert window is not None
    start, end, avg = window
    assert start == "2026-11-21T14:00"
    assert end == "2026-11-21T16:00"
    # Window is the same, but the average is now the indicative Indian
    # AQI average (14:00=149, 15:00=139, 16:00=159), not the US AQI average.
    assert avg == pytest.approx(149.0, abs=0.1)


def test_cleanest_window_too_few_points(delhi_city):
    parsed = parse_air_quality({
        "current": {"time": "2026-11-21T08:00"},
        "hourly": {"time": ["2026-11-21T08:00"], "us_aqi": [120]},
    }, delhi_city)
    assert parsed.cleanest_window(3) is None


def test_daily_trend_two_days(report):
    trend = report.daily_trend()
    assert len(trend) == 2
    assert trend[0][0] == "2026-11-21"
    assert trend[0][1] == 235  # max AQI day 1
    assert trend[1][0] == "2026-11-22"
    assert trend[1][1] == 110


def test_quick_city_known_and_unknown():
    delhi = quick_city("Delhi")
    assert delhi.latitude == pytest.approx(28.65)
    assert delhi.country == "India"
    assert len(api_module.QUICK_CITIES) == 10
    with pytest.raises(KeyError):
        quick_city("Atlantis")


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_search_cities_parses_results():
    payload = {"results": [
        {"name": "Jaipur", "country": "India", "country_code": "IN",
         "latitude": 26.91, "longitude": 75.79, "timezone": "Asia/Kolkata",
         "admin1": "Rajasthan"},
    ]}
    with patch.object(api_module.requests, "get",
                      return_value=_FakeResponse(payload)):
        cities = search_cities("Jaipur")
    assert len(cities) == 1
    assert cities[0].name == "Jaipur"
    assert cities[0].admin1 == "Rajasthan"


def test_search_cities_blank_query_returns_empty():
    assert search_cities("") == []
    assert search_cities("   ") == []


def test_search_cities_no_results():
    with patch.object(api_module.requests, "get",
                      return_value=_FakeResponse({"results": []})):
        assert search_cities("Xyzzy") == []


def test_search_cities_network_error_raises_api_error():
    with patch.object(api_module.requests, "get",
                      side_effect=requests.ConnectionError("offline")):
        with pytest.raises(ApiError):
            search_cities("Delhi")


def test_fetch_air_uses_both_endpoints(api_response, delhi_city):
    weather = {"current": {"time": "2026-11-21T08:15", "temperature_2m": 18.3,
                           "relative_humidity_2m": 79, "wind_speed_10m": 5.2,
                           "wind_direction_10m": 88, "weather_code": 0}}
    calls = {"n": 0}

    def fake_get(url, params=None, timeout=None):
        calls["n"] += 1
        if "air-quality" in url:
            return _FakeResponse(api_response)
        return _FakeResponse(weather)

    with patch.object(api_module.requests, "get", side_effect=fake_get):
        report = fetch_air(delhi_city)
    assert calls["n"] == 2
    assert report.current.us_aqi == 219
    assert report.weather.temperature_c == 18.3
    assert report.weather.wind_kmh == 5.2


def test_fetch_air_weather_failure_keeps_report(api_response, delhi_city):
    def fake_get(url, params=None, timeout=None):
        if "air-quality" in url:
            return _FakeResponse(api_response)
        raise requests.ConnectionError("weather down")

    with patch.object(api_module.requests, "get", side_effect=fake_get):
        report = fetch_air(delhi_city)
    assert report.current.us_aqi == 219
    assert report.weather.temperature_c is None


def test_fetch_air_failure_raises_api_error(delhi_city):
    with patch.object(api_module.requests, "get",
                      side_effect=requests.Timeout("slow")):
        with pytest.raises(ApiError):
            fetch_air(delhi_city)


def test_sample_report_is_flagged_not_live(delhi_city):
    sample = sample_report(delhi_city)
    assert sample.is_live is False
    assert "SAMPLE" in sample.source
    assert sample.current.us_aqi == 312
    assert len(sample.hourly) == 24


def test_sample_report_unknown_city_uses_default():
    sample = sample_report(City(name="Nowhere", country="", latitude=0,
                                longitude=0))
    assert sample.is_live is False
    assert sample.current.us_aqi is not None


def test_sample_report_has_best_and_worst_hours(delhi_city):
    sample = sample_report(delhi_city)
    assert sample.best_hour_today() is not None
    assert sample.worst_hour_today() is not None
    assert sample.cleanest_window(3) is not None


# --- v3: India-only, calculated Indian AQI ----------------------------------


def test_parse_computes_indian_aqi(report):
    indian = report.indian_aqi
    assert indian.available is True
    assert indian.dominant == "pm2_5"
    assert indian.category == "Poor"
    assert indian.value is not None and 201 <= indian.value <= 300
    assert "Partial means" in indian.basis  # only 9 hours before 08:30
    assert indian.sub_indices["pm2_5"] == indian.value


def test_primary_aqi_is_indian_first(report):
    value, scale, category = report.primary_aqi()
    assert scale == "Indian AQI (CPCB)"
    assert value == float(report.indian_aqi.value)
    assert category == report.indian_aqi.category


def test_primary_aqi_falls_back_to_us(delhi_city):
    parsed = parse_air_quality({
        "current": {"time": "2026-11-21T08:00", "us_aqi": 120},
        "hourly": {"time": ["2026-11-21T08:00"], "us_aqi": [120]},
    }, delhi_city)
    value, scale, category = parsed.primary_aqi()
    assert scale == "US AQI"
    assert value == 120.0
    assert category == "Unhealthy for Sensitive Groups"


def test_hourly_points_carry_indicative_indian_aqi(report):
    point = report.hourly[8]  # 08:00, worst hour
    assert point.indian_aqi is not None
    assert point.primary_aqi == point.indian_aqi


def test_daily_trend_includes_indian_max(report):
    trend = report.daily_trend()
    assert len(trend[0]) == 4
    assert trend[0][3] is not None  # max indicative Indian AQI, day 1


def test_search_filters_non_indian_results():
    from planner.api import search_cities_with_note
    payload = {"results": [
        {"name": "London", "country": "United Kingdom", "country_code": "GB",
         "latitude": 51.5, "longitude": -0.12},
        {"name": "Patna", "country": "India", "country_code": "IN",
         "latitude": 25.59, "longitude": 85.14, "admin1": "Bihar"},
    ]}
    with patch.object(api_module.requests, "get",
                      return_value=_FakeResponse(payload)):
        cities, had_non_indian = search_cities_with_note("Patna")
    assert [c.name for c in cities] == ["Patna"]
    assert had_non_indian is True


def test_search_all_non_indian_returns_empty_with_note():
    from planner.api import search_cities_with_note
    payload = {"results": [
        {"name": "London", "country": "United Kingdom", "country_code": "GB",
         "latitude": 51.5, "longitude": -0.12},
    ]}
    with patch.object(api_module.requests, "get",
                      return_value=_FakeResponse(payload)):
        cities, had_non_indian = search_cities_with_note("London")
    assert cities == []
    assert had_non_indian is True


def test_bundled_indian_cities_database():
    from planner.api import INDIAN_CITIES, city_from_bundled
    total = sum(len(v) for v in INDIAN_CITIES.values())
    assert total == 45
    assert len(INDIAN_CITIES) == 22
    for state, entries in INDIAN_CITIES.items():
        for name, lat, lon in entries:
            assert 6.0 <= lat <= 37.5, name
            assert 68.0 <= lon <= 97.5, name
    delhi = city_from_bundled("Delhi")
    assert delhi is not None and delhi.latitude == 28.65
    assert city_from_bundled("Toronto") is None
    assert "Toronto" not in str(INDIAN_CITIES)


def test_quick_cities_are_india_only():
    assert set(api_module.QUICK_CITIES) == {
        "Delhi", "Mumbai", "Bengaluru", "Kolkata", "Chennai", "Hyderabad",
        "Pune", "Lucknow", "Patna", "Jaipur"}
    assert all(c == "India" for _, _, c in api_module.QUICK_CITIES.values())


def test_data_confidence_labels(report):
    conf = report.data_confidence()
    assert conf["indian_aqi"] == "estimated"
    assert conf["pm2_5"] == "modelled"
    assert conf["weather"] == "missing"  # fixture has no weather call


def test_sample_report_has_indian_aqi(delhi_city):
    sample = sample_report(delhi_city)
    assert sample.indian_aqi.available is True
    assert sample.data_confidence()["indian_aqi"] == "sample"


def test_fetch_air_requests_past_hours_and_ist(api_response, delhi_city):
    seen = {}

    def fake_get(url, params=None, timeout=None):
        if "air-quality" in url:
            seen.update(params or {})
            return _FakeResponse(api_response)
        return _FakeResponse({"current": {}})

    with patch.object(api_module.requests, "get", side_effect=fake_get):
        fetch_air(delhi_city)
    assert seen["past_hours"] == 24
    assert seen["forecast_days"] == 5
    assert seen["timezone"] == "Asia/Kolkata"
    assert "carbon_monoxide" in seen["hourly"]
    assert "ozone" in seen["hourly"]
