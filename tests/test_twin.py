"""Clean Air Digital Twin — educational simulation, labelled as such."""
from planner.twin import (
    SCENARIOS,
    TWIN_LABEL,
    improvement_suggestions,
    simulate,
)


def test_twin_label_says_educational():
    assert "EDUCATIONAL SIMULATION" in TWIN_LABEL
    assert "not a scientific prediction" in TWIN_LABEL


def test_simulate_zero_change(report):
    result = simulate(report)
    assert result is not None
    assert result.simulated_aqi == 268
    assert result.delta == 0
    assert result.base_category == "Poor"


def test_simulate_metro_shift_improves(report):
    result = simulate(report, metro_shift=40)
    assert result.delta == -20  # 40 * -0.5
    assert result.simulated_aqi == 248
    assert result.simulated_category == "Poor"  # still Poor (201-300)


def test_simulate_traffic_worsens(report):
    result = simulate(report, traffic=30)
    assert result.delta == 18  # 30 * 0.6
    assert result.simulated_aqi == 286


def test_simulate_caps_at_500(report):
    result = simulate(report, traffic=30, household=30)
    assert result.simulated_aqi <= 500


def test_simulate_no_data_returns_none(report):
    from planner.indian_aqi import IndianAQI
    report.current.us_aqi = None
    report.indian_aqi = IndianAQI(
        value=None, category="Unavailable", colour="#E5E7EB",
        text_colour="#1A1A1A", symbol="?", dominant="none",
        available=False, reason="Insufficient data for Indian AQI.")
    assert simulate(report) is None


def test_scenarios_disclose_weights():
    for info in SCENARIOS.values():
        assert info["note"].strip()
        assert "weight" in info or "moves AQI" in info["note"]


def test_improvement_suggestions_mention_levers(report):
    result = simulate(report, metro_shift=20, green_cover=10)
    suggestions = improvement_suggestions(result)
    assert any("metro" in s.lower() for s in suggestions)
    assert any("green" in s.lower() for s in suggestions)
