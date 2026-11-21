"""Environmental Impact Score maths and grades."""
import pytest

from planner.score import co2_savings_series, grade_for, impact_score


def test_grade_bands():
    assert grade_for(90) == "Clean-air champion"
    assert grade_for(80) == "Clean-air champion"
    assert grade_for(70) == "On track"
    assert grade_for(50) == "Getting going"
    assert grade_for(10) == "Just starting"


def test_impact_score_clean_commute_scores_high():
    score = impact_score("Metro", 7, 4, 4, 3)
    assert score.total >= 80
    assert score.commute_points == 27


def test_impact_score_car_scores_low():
    score = impact_score("Car (petrol/diesel)", 0, 0, 4, 0)
    assert score.total == 8
    assert score.suggestions  # improvement suggestions present


def test_impact_score_caps_at_100():
    score = impact_score("Work from home", 30, 10, 4, 10)
    assert score.total == 100


def test_impact_score_habits_capped():
    score = impact_score("Metro", 100, 0, 0, 0)
    assert score.habits_points == 30


def test_co2_savings_series_weekdays_only():
    series = co2_savings_series(10.0)
    # (0.17 - 0.03) * 10 * 2 = 2.8 kg per weekday
    assert series["Mon"] == 2.8
    assert series["Fri"] == 2.8
    assert series["Sat"] == 0.0
    assert series["Sun"] == 0.0
    assert len(series) == 7
