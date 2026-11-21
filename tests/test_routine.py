"""Profile rules and day-plan generation."""
import pytest

from planner.indian_aqi import IndianAQI, category_for
from planner.routine import (
    COMMUTE_MODES,
    SENSITIVITIES,
    Profile,
    build_day_plan,
)


def set_indian_aqi(report, value: int | None) -> None:
    """Set the report's calculated Indian AQI (primary display)."""
    if value is None:
        report.indian_aqi = IndianAQI(
            value=None, category="Unavailable", colour="#E5E7EB",
            text_colour="#1A1A1A", symbol="?", dominant="none",
            available=False, reason="Insufficient data for Indian AQI.")
        report.current.us_aqi = None
        return
    cat, colour, text, symbol = category_for(value)
    report.indian_aqi = IndianAQI(
        value=value, category=cat, colour=colour, text_colour=text,
        symbol=symbol, dominant="pm2_5", available=True)
    report.current.us_aqi = float(value)


def test_sensitivities_and_modes_cover_expected():
    assert "General" in SENSITIVITIES
    assert "Asthma / respiratory condition" in SENSITIVITIES
    assert "Outdoor athlete" in SENSITIVITIES
    assert len(SENSITIVITIES) == 6
    assert "Work from home" in COMMUTE_MODES


@pytest.mark.parametrize("sensitivity,expected", [
    ("General", False),
    ("Sensitive groups", True),
    ("Asthma / respiratory condition", True),
    ("Child", True),
    ("Elderly", True),
    ("Outdoor athlete", False),
])
def test_is_sensitive(sensitivity, expected):
    assert Profile(sensitivity=sensitivity).is_sensitive() is expected


@pytest.mark.parametrize("sensitivity,limit", [
    ("General", 200), ("Outdoor athlete", 200),
    ("Sensitive groups", 100), ("Asthma / respiratory condition", 100),
    ("Child", 100), ("Elderly", 100),
])
def test_exercise_and_mask_limits_indian(sensitivity, limit):
    """Indian (CPCB) limits are the default: Moderate tops at 200."""
    profile = Profile(sensitivity=sensitivity)
    assert profile.exercise_limit() == limit
    assert profile.mask_limit() == limit


@pytest.mark.parametrize("sensitivity,limit", [
    ("General", 150), ("Outdoor athlete", 150),
    ("Sensitive groups", 100), ("Asthma / respiratory condition", 100),
    ("Child", 100), ("Elderly", 100),
])
def test_exercise_and_mask_limits_us_fallback(sensitivity, limit):
    """US (EPA) limits apply when the Indian AQI is unavailable."""
    profile = Profile(sensitivity=sensitivity)
    assert profile.exercise_limit(indian=False) == limit
    assert profile.mask_limit(indian=False) == limit


def test_build_plan_headline_and_category(profile, report):
    plan = build_day_plan(profile, report)
    # Primary display is the calculated Indian AQI (268, Poor), not US 219.
    assert plan.aqi_now == 268
    assert plan.category == "Poor"
    assert "Delhi" in plan.headline
    assert "Indian AQI (CPCB)" in plan.headline
    assert "general" in plan.headline


def test_build_plan_has_core_items(profile, report):
    plan = build_day_plan(profile, report)
    titles = [item.title for item in plan.items]
    assert any("Commute" in t for t in titles)
    assert any("Exercise" in t for t in titles)
    assert any("Ventilation" in t for t in titles)
    assert any("Outdoor time" in t for t in titles)


def test_every_item_has_action_and_impact(profile, report):
    plan = build_day_plan(profile, report)
    for item in plan.items:
        assert item.action.strip()
        assert item.impact.strip()
        assert len(item.impact) > 20


def test_mask_item_appears_when_aqi_high(profile, report):
    plan = build_day_plan(profile, report)  # Indian AQI 268 > 200
    assert any("Mask" in item.title for item in plan.items)


def test_mask_item_absent_when_aqi_low(profile, report):
    set_indian_aqi(report, 40)
    plan = build_day_plan(profile, report)
    assert not any("Mask" in item.title for item in plan.items)


def test_exercise_moves_indoors_when_above_limit(profile, report):
    plan = build_day_plan(profile, report)  # Indian AQI 268 > 200
    exercise = next(i for i in plan.items if "Exercise" in i.title)
    assert "indoors" in exercise.action.lower()
    assert "2 PM" in exercise.action or "3 PM" in exercise.action


def test_exercise_outdoors_when_within_limit(profile, report):
    set_indian_aqi(report, 80)
    for point in report.hourly:
        point.us_aqi = 80
        point.indian_aqi = 80
    plan = build_day_plan(profile, report)
    exercise = next(i for i in plan.items if "Exercise" in i.title)
    assert "outdoors" in exercise.action.lower()


def test_exercise_indoors_profile_stays_indoors(report):
    profile = Profile(exercises_outdoors=False, exercise_minutes=20)
    plan = build_day_plan(profile, report)
    exercise = next(i for i in plan.items if "Exercise" in i.title)
    assert "indoors" in exercise.action.lower()
    assert "20" in exercise.action


def test_ventilation_closed_when_aqi_over_200(profile, report):
    plan = build_day_plan(profile, report)
    vent = next(i for i in plan.items if "Ventilation" in i.title)
    assert "closed" in vent.action.lower()


def test_ventilation_uses_cleanest_hour_when_moderate(profile, report):
    set_indian_aqi(report, 90)
    plan = build_day_plan(profile, report)
    vent = next(i for i in plan.items if "Ventilation" in i.title)
    assert "3 PM" in vent.action  # best hour today is 15:00
    assert "139" in vent.impact  # indicative Indian AQI at 15:00


@pytest.mark.parametrize("mode", COMMUTE_MODES)
def test_commute_item_for_every_mode(mode, report):
    profile = Profile(commute_mode=mode)
    plan = build_day_plan(profile, report)
    commute = next(i for i in plan.items if "Commute" in i.title)
    assert commute.action.strip()
    assert commute.impact.strip()


def test_work_from_home_commute_has_no_exposure(report):
    profile = Profile(commute_mode="Work from home")
    plan = build_day_plan(profile, report)
    commute = next(i for i in plan.items if "Commute" in i.title)
    assert "no commute" in commute.action.lower()


def test_outdoor_time_stay_in_when_very_high(profile, report):
    set_indian_aqi(report, 350)  # Very Poor: above the 300 stay-in limit
    plan = build_day_plan(profile, report)
    outdoor = next(i for i in plan.items if "Outdoor time" in i.title)
    assert "essential" in outdoor.action.lower()


def test_outdoor_time_avoids_worst_hour(profile, report):
    set_indian_aqi(report, 120)
    plan = build_day_plan(profile, report)
    outdoor = next(i for i in plan.items if "Outdoor time" in i.title)
    assert "8 AM" in outdoor.action  # worst hour today is 08:00


def test_plan_handles_missing_aqi(profile, report):
    set_indian_aqi(report, None)
    plan = build_day_plan(profile, report)
    assert plan.category == "Unavailable"
    assert "No current AQI reading" in plan.headline
    assert len(plan.items) >= 4
