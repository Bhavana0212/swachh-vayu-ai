"""School Air Safety Planner."""
from planner.school import SCHOOL_CHECKLIST, school_plan


def test_school_plan_poor_day_moves_indoors(report):
    plan = school_plan(report)  # Indian AQI 268 > 200
    assert plan.aqi == 268
    assert "indoors" in plan.assembly.lower()
    assert "indoors" in plan.sports.lower()
    assert "Delhi" in plan.parent_summary


def test_school_plan_moderate_day_shortens(report):
    from planner.indian_aqi import IndianAQI, category_for
    cat, colour, text, symbol = category_for(150)
    report.indian_aqi = IndianAQI(
        value=150, category=cat, colour=colour, text_colour=text,
        symbol=symbol, dominant="pm2_5", available=True)
    plan = school_plan(report)
    assert "short" in plan.assembly.lower()
    assert "Shorten" in plan.sports
    assert plan.best_window  # cleanest 2-hour window exists


def test_school_plan_good_day_normal(report):
    from planner.indian_aqi import IndianAQI, category_for
    cat, colour, text, symbol = category_for(45)
    report.indian_aqi = IndianAQI(
        value=45, category=cat, colour=colour, text_colour=text,
        symbol=symbol, dominant="pm2_5", available=True)
    plan = school_plan(report)
    assert "as usual" in plan.assembly.lower()
    assert "as usual" in plan.sports.lower()


def test_school_plan_no_data(report):
    from planner.indian_aqi import IndianAQI
    report.current.us_aqi = None
    report.indian_aqi = IndianAQI(
        value=None, category="Unavailable", colour="#E5E7EB",
        text_colour="#1A1A1A", symbol="?", dominant="none",
        available=False, reason="Insufficient data for Indian AQI.")
    plan = school_plan(report)
    assert plan.aqi is None
    assert "No reading" in plan.assembly


def test_school_checklist_nonempty():
    assert len(SCHOOL_CHECKLIST) >= 6
    assert any("mask" in item.lower() for item in SCHOOL_CHECKLIST)
