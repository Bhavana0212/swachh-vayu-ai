"""Forecast predictor, anomaly detection, seasons, morning briefing."""
from planner.forecast import (
    SEASONS,
    detect_anomalies,
    detect_spikes,
    morning_briefing,
    season_for_month,
    seasonal_analysis,
)


def test_detect_spikes_none_on_flat_forecast(report):
    # Day 2 (110 US) is lower than day 1, so no upward spike.
    assert detect_spikes(report) == []


def test_detect_spikes_finds_jump(report):
    # Raise day-2 hourly values so its max jumps >20% over day 1.
    for point in report.hourly:
        if point.time.startswith("2026-11-22"):
            point.us_aqi = 400
            point.indian_aqi = 450
    spikes = detect_spikes(report)
    assert len(spikes) == 1
    assert spikes[0].day == "2026-11-22"
    assert spikes[0].rise_pct > 20


def test_detect_anomalies_none_on_normal(report):
    assert detect_anomalies(report) == []


def test_detect_anomalies_flags_jump(report):
    report.current.pm2_5 = 300.0  # far above the recent mean (~110)
    anomalies = detect_anomalies(report)
    assert len(anomalies) == 1
    assert anomalies[0].direction == "up"
    assert "jumped" in anomalies[0].title.lower()


def test_season_for_month():
    assert season_for_month(1) == "winter"
    assert season_for_month(5) == "summer"
    assert season_for_month(8) == "monsoon"
    assert season_for_month(11) == "post_monsoon"


def test_seasons_cover_all_months():
    assert set(SEASONS) == {"winter", "summer", "monsoon", "post_monsoon"}
    for info in SEASONS.values():
        assert info["pattern"].strip()
        assert info["advice"].strip()


def test_seasonal_analysis_for_november(report):
    analysis = seasonal_analysis(report, 11)
    assert analysis["season"] == "Post Monsoon"
    assert "268" in analysis["today"]
    assert "worst day" in analysis["forecast_note"].lower()


def test_morning_briefing(profile, report):
    briefing = morning_briefing(report, profile)
    assert "268" in briefing["headline"]
    assert "Delhi" in briefing["headline"]
    assert "3 PM" in briefing["timing"]  # cleanest hour
    assert "8 AM" in briefing["timing"]  # worst hour
    assert briefing["routine"].strip()
    assert briefing["plan_headline"].strip()
