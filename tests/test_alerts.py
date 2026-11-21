"""In-app smart alerts (no push)."""
from planner.alerts import build_alerts


def test_daily_summary_always_present(profile, report):
    alerts = build_alerts(report, profile)
    assert alerts[0].severity == "info"
    assert "Delhi" in alerts[0].title
    assert "268" in alerts[0].title  # Indian AQI (primary)
    assert "Indian AQI (CPCB)" in alerts[0].title


def test_poor_air_alert_at_high_aqi(profile, report):
    alerts = build_alerts(report, profile)
    titles = [a.title for a in alerts]
    assert any("Poor air" in t for t in titles)
    poor = next(a for a in alerts if "Poor air" in a.title)
    assert poor.severity == "warning"  # 268: warning, not critical (>300)


def test_critical_alert_at_severe(profile, report):
    from planner.indian_aqi import IndianAQI, category_for
    cat, colour, text, symbol = category_for(450)
    report.indian_aqi = IndianAQI(
        value=450, category=cat, colour=colour, text_colour=text,
        symbol=symbol, dominant="pm2_5", available=True)
    alerts = build_alerts(report, profile)
    poor = next(a for a in alerts if "Poor air" in a.title)
    assert poor.severity == "critical"


def test_pm25_alert_present(profile, report):
    alerts = build_alerts(report, profile)
    assert any("PM2.5" in a.title for a in alerts)


def test_exercise_limit_alert(profile, report):
    alerts = build_alerts(report, profile)
    assert any("exercise above your limit" in a.title.lower() for a in alerts)


def test_ventilation_tip_points_to_cleanest_hour(profile, report):
    alerts = build_alerts(report, profile)
    tips = [a for a in alerts if "air out" in a.title.lower()]
    assert tips
    assert "3 PM" in tips[0].title  # cleanest hour 15:00


def test_no_data_alert_when_unavailable(profile, report):
    from planner.indian_aqi import IndianAQI
    report.current.us_aqi = None
    report.indian_aqi = IndianAQI(
        value=None, category="Unavailable", colour="#E5E7EB",
        text_colour="#1A1A1A", symbol="?", dominant="none",
        available=False, reason="Insufficient data for Indian AQI.")
    alerts = build_alerts(report, profile)
    assert alerts[0].title == "No current AQI reading"
    assert alerts[0].severity == "warning"
