"""What If simulator: mode, time-of-day and cooking comparisons."""
from planner.whatif import (
    compare_modes,
    compare_times,
    cooking_ventilation_scenario,
    lowest_emission_mode,
    lowest_exposure_mode,
)


def test_compare_modes_covers_all_modes():
    rows = compare_modes(10.0, "Car (petrol/diesel)")
    assert len(rows) == 10
    car = next(r for r in rows if r.mode == "Car (petrol/diesel)")
    assert car.co2_per_week_kg == 17.0  # 0.17 * 20 * 5
    metro = next(r for r in rows if r.mode == "Metro")
    assert metro.co2_per_week_kg == 3.0  # 0.03 * 20 * 5
    assert metro.saving_vs_current_kg_week == 14.0


def test_compare_modes_zero_km():
    rows = compare_modes(0.0, "Car (petrol/diesel)")
    assert all(r.co2_per_week_kg == 0.0 for r in rows)


def test_lowest_emission_is_wfh_or_active():
    rows = compare_modes(10.0, "Car (petrol/diesel)")
    best = lowest_emission_mode(rows)
    assert best.mode == "Work from home"
    assert best.co2_per_week_kg == 0.0


def test_lowest_exposure_motorised():
    rows = compare_modes(10.0, "Car (petrol/diesel)")
    best = lowest_exposure_mode(rows)
    assert best.exposure_level == "Low"
    assert best.mode != "Work from home"


def test_compare_times_morning_vs_evening(report):
    comparison = compare_times(report, 7, 18)
    assert comparison.aqi_a is not None
    assert comparison.aqi_b is not None
    # 07:00 indicative Indian AQI 310 vs 18:00 260: evening is cleaner
    # in this fixture.
    assert "6 PM" in comparison.recommendation
    assert "lower" in comparison.recommendation


def test_compare_times_missing_hour(report):
    comparison = compare_times(report, 7, 25)
    assert comparison.aqi_b is None
    assert "No forecast" in comparison.recommendation


def test_cooking_scenario_chimney_reduces():
    result = cooking_ventilation_scenario(100.0)
    assert result.without_chimney_pm25 > result.with_chimney_pm25
    assert result.reduction_pct > 0
    assert "Estimate only" in result.note


def test_compare_times_negligible_difference(report):
    # 320 vs 321 is a <1% difference — the wording must not claim "0% lower".
    for point in report.hourly:
        if point.time[11:13] == "07":
            point.indian_aqi = 320
        if point.time[11:13] == "18":
            point.indian_aqi = 321
    comparison = compare_times(report, 7, 18)
    assert "nearly the same" in comparison.recommendation
