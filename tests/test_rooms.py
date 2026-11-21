"""Room-by-room planner, cooking, sources, ventilation, home score."""
from planner.rooms import (
    COOKING_TIPS,
    ROOMS,
    SOURCE_CHECKLIST,
    home_clean_air_score,
    room_plan,
    ventilation_advice,
)


def test_rooms_cover_spec_list():
    assert ROOMS == ["Bedroom", "Kitchen", "Living room", "Children's room",
                     "Study room"]


def test_room_plan_kitchen_worst_without_purifier():
    kitchen = room_plan("Kitchen", 100.0, purifier=False)
    bedroom = room_plan("Bedroom", 100.0, purifier=False)
    assert kitchen.estimated_pm25 > bedroom.estimated_pm25
    assert kitchen.risk.strip()
    assert kitchen.advice.strip()


def test_room_plan_purifier_lowers_estimate():
    with_purifier = room_plan("Bedroom", 100.0, purifier=True)
    without = room_plan("Bedroom", 100.0, purifier=False)
    assert with_purifier.estimated_pm25 < without.estimated_pm25


def test_room_plan_unknown_room_defaults_to_living():
    plan = room_plan("Balcony", 100.0)
    assert plan.room == "Balcony"
    assert plan.estimated_pm25 > 0


def test_ventilation_advice_closed_when_poor(report):
    advice = ventilation_advice(report)  # Indian AQI 268
    assert "closed" in advice["verdict"].lower()
    assert advice["best_time"] == "3 PM"


def test_ventilation_advice_opens_when_moderate(report):
    from planner.indian_aqi import IndianAQI, category_for
    cat, colour, text, symbol = category_for(90)
    report.indian_aqi = IndianAQI(
        value=90, category=cat, colour=colour, text_colour=text,
        symbol=symbol, dominant="pm2_5", available=True)
    advice = ventilation_advice(report)
    assert "3 PM" in advice["verdict"]


def test_cooking_tips_and_sources_nonempty():
    assert len(COOKING_TIPS) >= 4
    assert len(SOURCE_CHECKLIST) >= 6
    assert any("chimney" in tip[0].lower() for tip in COOKING_TIPS)
    assert any("Incense" in item[0] for item in SOURCE_CHECKLIST)


def test_home_clean_air_score_bounds():
    score, verdict, improvements = home_clean_air_score(
        True, True, True, True, True)
    assert score == 100
    assert improvements == []
    assert "Excellent" in verdict
    score, verdict, improvements = home_clean_air_score(
        False, False, False, False, False)
    assert score == 0
    assert len(improvements) == 5
    score, _, _ = home_clean_air_score(True, False, True, False, False)
    assert score == 40
