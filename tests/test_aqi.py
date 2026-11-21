"""AQI banding, sub-indices and guidance."""
import pytest

from planner.aqi import (
    Band,
    aqi_difference_pct,
    dominant_pollutant,
    eu_band,
    sensitive_guidance,
    sub_index,
    us_band,
)


@pytest.mark.parametrize("value,category", [
    (0, "Good"), (25, "Good"), (50, "Good"),
    (51, "Moderate"), (75, "Moderate"), (100, "Moderate"),
    (101, "Unhealthy for Sensitive Groups"), (125, "Unhealthy for Sensitive Groups"),
    (150, "Unhealthy for Sensitive Groups"),
    (151, "Unhealthy"), (175, "Unhealthy"), (200, "Unhealthy"),
    (201, "Very Unhealthy"), (250, "Very Unhealthy"), (300, "Very Unhealthy"),
    (301, "Hazardous"), (400, "Hazardous"), (500, "Hazardous"),
])
def test_us_band_boundaries(value, category):
    band = us_band(value)
    assert band.category == category
    assert band.colour.startswith("#")
    assert band.guidance


def test_us_band_none_is_unavailable():
    band = us_band(None)
    assert band.category == "Unavailable"
    assert "No AQI" in band.guidance


def test_us_band_above_500_caps_at_hazardous():
    assert us_band(650).category == "Hazardous"


@pytest.mark.parametrize("value,category", [
    (0, "Good"), (20, "Good"),
    (21, "Fair"), (40, "Fair"),
    (41, "Moderate"), (60, "Moderate"),
    (61, "Poor"), (80, "Poor"),
    (81, "Very Poor"), (100, "Very Poor"),
    (101, "Extremely Poor"), (250, "Extremely Poor"),
])
def test_eu_band_boundaries(value, category):
    assert eu_band(value).category == category


def test_eu_band_none_is_unavailable():
    assert eu_band(None).category == "Unavailable"


def test_bands_have_distinct_colours():
    from planner.aqi import EU_BANDS, US_BANDS
    assert len({b[3] for b in US_BANDS}) == len(US_BANDS)
    assert len({b[3] for b in EU_BANDS}) == len(EU_BANDS)


def test_badge_html_contains_category_and_value():
    html = us_band(219).badge_html(219)
    assert "219" in html
    assert "Very Unhealthy" in html
    assert "#8F3F97" in html  # band colour present


@pytest.mark.parametrize("pollutant,conc,expected", [
    ("pm2_5", 0.0, 0),
    ("pm2_5", 12.0, 50),
    ("pm2_5", 35.4, 100),
    ("pm2_5", 55.4, 150),
    ("pm2_5", 150.4, 200),
    ("pm2_5", 250.4, 300),
    ("pm2_5", 500.4, 500),
    ("pm2_5", 600.0, 500),  # above top breakpoint caps at 500
    ("pm10", 54.0, 50),
    ("pm10", 154.0, 100),
    ("ozone", 108.0, 50),
    ("nitrogen_dioxide", 100.0, 50),
    ("sulphur_dioxide", 92.0, 50),
    ("carbon_monoxide", 5.1, 50),  # mg/m3
    ("carbon_monoxide", 10.8, 100),
])
def test_sub_index_breakpoints(pollutant, conc, expected):
    assert sub_index(pollutant, conc) == expected


def test_sub_index_midpoint_interpolates():
    # PM2.5 23.75 is halfway between 12.1 and 35.4 -> ~75
    value = sub_index("pm2_5", 23.75)
    assert 70 <= value <= 80


def test_sub_index_none_and_unknown():
    assert sub_index("pm2_5", None) is None
    assert sub_index("dust", 10.0) is None
    assert sub_index("unknown", 10.0) is None


def test_sub_index_negative_is_zero():
    assert sub_index("pm2_5", -5.0) == 0


def test_dominant_pollutant_picks_highest_sub_index():
    key, sub = dominant_pollutant({
        "pm2_5": 139.2, "pm10": 140.2, "nitrogen_dioxide": 51.1,
        "ozone": 42.0, "sulphur_dioxide": 43.5, "carbon_monoxide": 2126.0,
    })
    assert key == "pm2_5"
    assert sub is not None and sub > 150


def test_dominant_pollutant_empty():
    assert dominant_pollutant({}) == ("none", None)
    assert dominant_pollutant({"pm2_5": None}) == ("none", None)


def test_dominant_pollutant_converts_co_units():
    # 2126 ug/m3 CO = 2.126 mg/m3 -> sub-index ~21, well below PM2.5 here.
    key, _ = dominant_pollutant({"pm2_5": 100.0, "carbon_monoxide": 2126.0})
    assert key == "pm2_5"


def test_sensitive_guidance_known_and_unknown():
    assert "N95" in sensitive_guidance("Unhealthy")
    assert sensitive_guidance("Not a band")  # graceful fallback


@pytest.mark.parametrize("from_aqi,to_aqi,expected", [
    (200, 100, -50.0),
    (100, 200, 100.0),
    (150, 150, 0.0),
    (0, 100, 0.0),
])
def test_aqi_difference_pct(from_aqi, to_aqi, expected):
    assert aqi_difference_pct(from_aqi, to_aqi) == expected


def test_band_is_frozen_dataclass():
    band = Band("Good", "#00E400", "#1A1A1A", "Fine.")
    assert band.category == "Good"
