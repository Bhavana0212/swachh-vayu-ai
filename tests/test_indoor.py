"""Indoor estimator maths and hacks checklist."""
import pytest

from planner.indoor import (
    COOKING_ADDITION,
    INDOOR_HACKS,
    VENTILATION_FACTORS,
    estimate_indoor_pm25,
)


def test_estimator_windows_closed_no_purifier():
    est = estimate_indoor_pm25(100.0, "Windows closed", False,
                               "No cooking right now")
    assert est.estimated_pm25 == pytest.approx(35.0)
    assert est.ventilation_factor == 0.35


def test_estimator_windows_open_no_purifier():
    est = estimate_indoor_pm25(100.0, "Windows open", False,
                               "No cooking right now")
    assert est.estimated_pm25 == pytest.approx(90.0)


def test_estimator_purifier_halves_base():
    est = estimate_indoor_pm25(100.0, "Windows closed", True,
                               "No cooking right now")
    assert est.estimated_pm25 == pytest.approx(100 * 0.35 * 0.45, abs=0.1)


def test_estimator_gas_cooking_adds():
    est = estimate_indoor_pm25(100.0, "Windows closed", False, "Gas cooking")
    assert est.estimated_pm25 == pytest.approx(35.0 + 18.0)
    assert est.cooking_addition == 18.0


def test_estimator_frying_adds_most():
    est = estimate_indoor_pm25(0.0, "Windows closed", False,
                               "Frying / grilling")
    assert est.estimated_pm25 == pytest.approx(30.0)


def test_estimator_zero_outdoor_zero_indoor_without_cooking():
    est = estimate_indoor_pm25(0.0, "Windows open", False,
                               "No cooking right now")
    assert est.estimated_pm25 == 0.0


def test_estimator_unknown_inputs_use_defaults():
    est = estimate_indoor_pm25(100.0, "Mystery", False, "Mystery meal")
    assert est.ventilation_factor == 0.60
    assert est.cooking_addition == 0.0


def test_estimator_summary_shows_working():
    est = estimate_indoor_pm25(139.2, "Windows cracked / trickle vent", True,
                               "Electric / induction cooking")
    summary = est.summary()
    assert "139.2" in summary
    assert "0.60" in summary
    assert "purifier running" in summary
    assert "about" in summary


def test_hacks_list_has_titles_actions_and_reasons():
    assert len(INDOOR_HACKS) == 8
    for title, action, why_this, impact in INDOOR_HACKS:
        assert title.strip()
        assert action.strip()
        assert why_this.strip()
        assert impact.strip()


def test_hacks_include_honest_plant_note():
    titles = [t for t, _, _, _ in INDOOR_HACKS]
    assert any("Plants" in t for t in titles)
    plant = next(h for h in INDOOR_HACKS if "Plants" in h[0])
    assert "negligible" in plant[2]


def test_factor_tables_complete():
    assert set(VENTILATION_FACTORS) == {
        "Windows closed", "Windows cracked / trickle vent", "Windows open"}
    assert set(COOKING_ADDITION) == {
        "No cooking right now", "Electric / induction cooking",
        "Gas cooking", "Frying / grilling"}


# --- v2 additions: room size, occupants, smoking, before/after -------------


def test_estimator_small_room_concentrates():
    small = estimate_indoor_pm25(100.0, "Windows closed", False,
                                 "No cooking right now",
                                 room_size="Small (under 150 sq ft)")
    medium = estimate_indoor_pm25(100.0, "Windows closed", False,
                                  "No cooking right now",
                                  room_size="Medium (150–400 sq ft)")
    assert small.estimated_pm25 > medium.estimated_pm25


def test_estimator_smoking_adds_large_amount():
    smoking = estimate_indoor_pm25(0.0, "Windows closed", False,
                                   "No cooking right now", smoking=True)
    assert smoking.estimated_pm25 == pytest.approx(40.0)


def test_estimator_occupants_add_beyond_two():
    base = estimate_indoor_pm25(0.0, "Windows closed", False,
                                "No cooking right now", occupants=2)
    crowded = estimate_indoor_pm25(0.0, "Windows closed", False,
                                   "No cooking right now", occupants=5)
    assert crowded.estimated_pm25 - base.estimated_pm25 == pytest.approx(6.0)


def test_estimator_cooking_frequency_scales():
    once = estimate_indoor_pm25(0.0, "Windows closed", False, "Gas cooking",
                                cooking_frequency="Once today")
    thrice = estimate_indoor_pm25(0.0, "Windows closed", False, "Gas cooking",
                                  cooking_frequency="Three or more times today")
    assert thrice.cooking_addition == pytest.approx(once.cooking_addition * 2)


def test_improvement_comparison_reduces():
    from planner.indoor import improvement_comparison
    current, improved, reduction = improvement_comparison(
        139.2, "Windows open", False, "Gas cooking")
    assert improved.estimated_pm25 < current.estimated_pm25
    assert 0 < reduction <= 100


def test_risk_category_bands():
    from planner.indoor import risk_category_for
    assert risk_category_for(5.0)[0] == "Low"
    assert risk_category_for(20.0)[0] == "Moderate"
    assert risk_category_for(40.0)[0] == "High"
    assert risk_category_for(80.0)[0] == "Very high"
