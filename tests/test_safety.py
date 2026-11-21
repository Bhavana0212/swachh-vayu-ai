"""Smart Activity Planner verdicts from the hourly forecast."""
from planner.safety import ACTIVITIES, assess, hourly_aqi_at


def test_activities_cover_spec_list():
    for activity in ("Running", "Walking", "Cycling", "Yoga",
                     "Outdoor gym", "Children's outdoor play",
                     "Morning walk", "Gardening"):
        assert activity in ACTIVITIES


def test_hourly_aqi_at_uses_indicative_indian(profile, report):
    # 15:00 is the cleanest hour: indicative Indian AQI 139.
    assert hourly_aqi_at(report, 15) == 139
    assert hourly_aqi_at(report, 3) == 228


def test_assess_safe_at_clean_hour(profile, report):
    verdict = assess("Morning walk", 15, profile, report)
    assert verdict.verdict == "Safe"
    assert verdict.aqi_at_hour == 139
    assert verdict.why is not None
    assert verdict.why.why_this.strip()


def test_assess_avoid_at_worst_hour(profile, report):
    # 08:00 indicative Indian AQI is 316 — well above the General limit.
    verdict = assess("Running", 8, profile, report)
    assert verdict.verdict == "Avoid"
    assert verdict.aqi_at_hour == 316
    assert "3 PM" in verdict.advice or "cleanest" in verdict.advice.lower()


def test_assess_sensitive_profile_stricter(sensitive_profile, report):
    # Sensitive limit 100; at 15:00 (139) a run is at least Caution.
    verdict = assess("Running", 15, sensitive_profile, report)
    assert verdict.verdict in ("Caution", "Avoid")


def test_assess_no_data_when_no_hourly(profile, report):
    report.hourly = []
    verdict = assess("Running", 7, profile, report)
    assert verdict.verdict == "No data"
    assert verdict.aqi_at_hour is None


def test_assess_unknown_activity_defaults_medium(profile, report):
    verdict = assess("Kite flying", 15, profile, report)
    assert verdict.aqi_at_hour == 139
    assert verdict.verdict in ("Safe", "Caution", "Avoid")
