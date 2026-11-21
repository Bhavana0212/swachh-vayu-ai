"""Calculated Indian AQI (CPCB methodology) — verified breakpoint table.

Known concentrations -> known AQI/category. Breakpoints are the CPCB
table verified 20 Nov 2026; these tests pin them exactly.
"""
import pytest

from planner.indian_aqi import (
    calculate_indian_aqi,
    category_for,
    indian_aqi_from_single_hour,
    mean_over,
    sub_index,
)


def _hours(start_hour: int, count: int, value: float,
           day: str = "2026-11-21"):
    return [(f"{day}T{h:02d}:00", value)
            for h in range(start_hour, start_hour + count)]


@pytest.mark.parametrize("conc,expected", [
    (0.0, 0), (15.0, 25), (30.0, 50),
    (45.0, 75), (60.0, 100),           # Satisfactory 31-60 -> 51-100
    (75.0, 149), (90.0, 200),          # Moderate 61-90 -> 101-200
    (105.0, 249), (120.0, 300),        # Poor 91-120 -> 201-300
    (185.0, 350), (250.0, 400),        # Very Poor 121-250 -> 301-400
    (251.0, 402), (315.0, 451),        # Severe interpolated over 129 width
    (380.0, 500), (600.0, 500),        # capped at 500
])
def test_pm25_sub_index(conc, expected):
    assert sub_index("pm2_5", conc) == expected


def test_cpcb_worked_example():
    """CPCB's own worked example (About NAQI doc) must hold exactly:
    PM2.5 sub-index is 51 at 31, 100 at 60, 75 at 45 ug/m3."""
    assert sub_index("pm2_5", 31.0) == 51
    assert sub_index("pm2_5", 45.0) == 75
    assert sub_index("pm2_5", 60.0) == 100
    # Band starts across pollutants: the first value of each Satisfactory
    # band maps to AQI 51.
    assert sub_index("pm10", 51.0) == 51
    assert sub_index("nitrogen_dioxide", 41.0) == 51
    assert sub_index("ozone", 51.0) == 51
    assert sub_index("carbon_monoxide", 1.1) == 51
    assert sub_index("sulphur_dioxide", 41.0) == 51


@pytest.mark.parametrize("conc,expected", [
    (0.0, 0), (25.0, 25), (50.0, 50),
    (75.0, 75), (100.0, 100),
    (175.0, 150), (250.0, 200),
    (300.0, 250), (350.0, 300),
    (390.0, 350), (430.0, 400),
    (500.0, 489),  # Severe: 430-509 -> 401-500; 500 is inside the band
    (510.0, 500),  # at/above 509 the index caps at 500
])
def test_pm10_sub_index(conc, expected):
    assert sub_index("pm10", conc) == expected


@pytest.mark.parametrize("conc,expected", [
    (20.0, 25), (40.0, 50), (60.0, 75), (80.0, 100),
    (130.0, 150), (180.0, 200), (230.0, 250), (280.0, 300),
    (340.0, 350), (400.0, 400),
])
def test_no2_sub_index(conc, expected):
    assert sub_index("nitrogen_dioxide", conc) == expected


@pytest.mark.parametrize("conc,expected", [
    (25.0, 25), (50.0, 50), (75.0, 75), (100.0, 100),
    (134.0, 150), (168.0, 200), (188.0, 249), (208.0, 300),
    (478.0, 350), (748.0, 400),
])
def test_o3_sub_index(conc, expected):
    assert sub_index("ozone", conc) == expected


@pytest.mark.parametrize("conc_mg,expected", [
    (0.5, 25), (1.0, 50), (1.5, 73), (2.0, 100),
    (6.0, 150), (10.0, 200), (13.5, 250), (17.0, 300),
    (25.5, 350), (34.0, 400),
])
def test_co_sub_index_mg(conc_mg, expected):
    assert sub_index("carbon_monoxide", conc_mg) == expected


@pytest.mark.parametrize("conc,expected", [
    (20.0, 25), (40.0, 50), (60.0, 75), (80.0, 100),
    (230.0, 150), (380.0, 200), (590.0, 250), (800.0, 300),
    (1200.0, 350), (1600.0, 400),
])
def test_so2_sub_index(conc, expected):
    assert sub_index("sulphur_dioxide", conc) == expected


def test_sub_index_none_and_unknown():
    assert sub_index("pm2_5", None) is None
    assert sub_index("unknown", 10.0) is None
    assert sub_index("pm2_5", -5.0) == 0


@pytest.mark.parametrize("aqi,category", [
    (0, "Good"), (50, "Good"), (51, "Satisfactory"), (100, "Satisfactory"),
    (101, "Moderately polluted"), (200, "Moderately polluted"),
    (201, "Poor"), (300, "Poor"),
    (301, "Very Poor"), (400, "Very Poor"),
    (401, "Severe"), (500, "Severe"),
])
def test_category_for(aqi, category):
    assert category_for(aqi)[0] == category


def test_category_for_none_and_above_500():
    assert category_for(None)[0] == "Unavailable"
    assert category_for(650)[0] == "Severe"


def test_mean_over_24h_window():
    values = _hours(0, 24, 100.0) + _hours(0, 24, 200.0, day="2026-11-22")
    mean, count = mean_over(values, __import__("datetime").datetime(2026, 11, 22, 10, 0), 24)
    # Last 24h ending 22 Nov 10:00 = 21 Nov 11:00..22 Nov 10:00:
    # 13 values at 100 (11:00-23:00 on 21st) + 11 at 200 (00:00-10:00 on 22nd)
    assert count == 24
    assert mean == pytest.approx((13 * 100 + 11 * 200) / 24, abs=0.01)


def test_mean_over_skips_missing():
    values = [("2026-11-21T08:00", 100.0), ("2026-11-21T09:00", None),
              ("2026-11-21T10:00", 200.0)]
    mean, count = mean_over(values, __import__("datetime").datetime(2026, 11, 21, 10, 0), 24)
    assert count == 2
    assert mean == 150.0


def test_mean_over_empty():
    mean, count = mean_over([], __import__("datetime").datetime(2026, 11, 21, 10, 0), 24)
    assert mean is None
    assert count == 0


def _full_hourly(pm25=100.0, pm10=200.0, no2=60.0, so2=30.0, co_ug=1500.0,
                 o3=80.0):
    """24 hourly values (00:00-23:00) at constant concentrations."""
    return {
        "pm2_5": _hours(0, 24, pm25),
        "pm10": _hours(0, 24, pm10),
        "nitrogen_dioxide": _hours(0, 24, no2),
        "sulphur_dioxide": _hours(0, 24, so2),
        "carbon_monoxide": _hours(0, 24, co_ug),
        "ozone": _hours(0, 24, o3),
    }


def test_calculate_delhi_like_day():
    # PM2.5 100 -> sub 232 (Poor band 91-120); PM10 200 -> 167; NO2 60 -> 75;
    # SO2 30 -> 38; CO 1.5 mg -> 73; O3 80 -> 80. Overall = 232 Poor, PM2.5.
    result = calculate_indian_aqi(_full_hourly(), "2026-11-21T23:00")
    assert result.available is True
    assert result.value == 232
    assert result.category == "Poor"
    assert result.dominant == "pm2_5"
    assert result.sub_indices["pm2_5"] == 232
    assert result.sub_indices["pm10"] == 167
    assert result.means["carbon_monoxide"] == 1.5  # ug -> mg conversion
    assert result.hours_used["pm2_5"] == 24
    assert result.hours_used["ozone"] == 8
    assert "24-hr means" in result.basis


def test_calculate_good_day():
    result = calculate_indian_aqi(
        _full_hourly(pm25=10.0, pm10=20.0, no2=15.0, so2=10.0,
                     co_ug=500.0, o3=30.0),
        "2026-11-21T23:00")
    assert result.available is True
    assert result.category == "Good"
    assert result.value is not None and result.value <= 50


def test_calculate_severe_day_caps_at_500():
    result = calculate_indian_aqi(
        _full_hourly(pm25=600.0, pm10=900.0, no2=500.0, so2=2000.0,
                     co_ug=40000.0, o3=900.0),
        "2026-11-21T23:00")
    assert result.value == 500
    assert result.category == "Severe"


def test_calculate_insufficient_without_pm():
    hourly = _full_hourly()
    del hourly["pm2_5"]
    del hourly["pm10"]
    result = calculate_indian_aqi(hourly, "2026-11-21T23:00")
    assert result.available is False
    assert result.value is None
    assert "Insufficient data" in result.reason


def test_calculate_insufficient_fewer_than_3():
    hourly = {"pm2_5": _hours(0, 24, 50.0),
              "pm10": _hours(0, 24, 80.0)}
    result = calculate_indian_aqi(hourly, "2026-11-21T23:00")
    assert result.available is False
    assert result.value is None


def test_calculate_partial_window_flagged():
    hourly = _full_hourly()
    hourly["pm2_5"] = _hours(10, 14, 100.0)  # only 14 values
    result = calculate_indian_aqi(hourly, "2026-11-21T23:00")
    assert result.available is True
    assert "Partial means" in result.basis
    assert result.hours_used["pm2_5"] == 14


def test_single_hour_indicative():
    result = indian_aqi_from_single_hour({
        "pm2_5": 139.2, "pm10": 140.2, "nitrogen_dioxide": 51.1,
        "ozone": 42.0, "sulphur_dioxide": 43.5, "carbon_monoxide": 2126.0,
    })
    assert result.available is True
    # PM2.5 139.2 is in Very Poor 121-250 -> 301-400:
    # 301 + (139.2-121)/129*99 = 315
    assert result.value == 315
    assert result.category == "Very Poor"
    assert result.dominant == "pm2_5"
    assert "indicative" in result.basis.lower()


def test_single_hour_insufficient():
    result = indian_aqi_from_single_hour({"pm2_5": 50.0})
    assert result.available is False
    assert result.value is None


def test_badge_html_contains_value_and_category():
    result = calculate_indian_aqi(_full_hourly(), "2026-11-21T23:00")
    html = result.badge_html()
    assert "232" in html
    assert "Poor" in html
    assert "aria-label" in html
