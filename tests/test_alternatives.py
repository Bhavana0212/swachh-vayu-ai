"""Sustainable swaps and impact maths."""
import pytest

from planner.alternatives import (
    ALL_SWAPS,
    KG_CO2_PER_KM,
    commute_swap,
    swaps_for,
    weekly_co2_saving_kg,
)


def test_commute_swap_car_to_transit_has_number():
    swap = commute_swap("Car (petrol/diesel)", 10.0)
    assert swap is not None
    assert "metro or bus" in swap.action
    # (0.17 - 0.03) * 10 * 2 = 2.8 kg per swapped return trip
    assert "2.8 kg CO2" in swap.impact
    assert "0.17" in swap.impact  # assumption stated


def test_commute_swap_car_km_scales():
    swap = commute_swap("Car (petrol/diesel)", 20.0)
    assert "5.6 kg CO2" in swap.impact


def test_commute_swap_work_from_home_is_none():
    assert commute_swap("Work from home", 10.0) is None


def test_commute_swap_cyclist_keeps_active():
    swap = commute_swap("Cycle", 5.0)
    assert swap is not None
    assert "Zero tailpipe" in swap.impact


def test_commute_swap_bus_user_gets_active_leg():
    swap = commute_swap("Bus", 8.0)
    assert swap is not None
    assert "active leg" in swap.title.lower()


def test_commute_swap_electric_car_still_gets_swap():
    swap = commute_swap("Car (electric)", 10.0)
    assert swap is not None
    # (0.05 - 0.03) * 10 * 2 = 0.4 kg — small but real saving vs metro
    assert "0.4 kg CO2" in swap.impact


def test_weekly_saving_maths():
    # (0.17 - 0.03) * 10 * 2 * 5 = 14.0 kg/week
    assert weekly_co2_saving_kg(10.0) == 14.0
    assert weekly_co2_saving_kg(0.0) == 0.0
    assert weekly_co2_saving_kg(10.0, days_per_week=3) == 8.4
    assert weekly_co2_saving_kg(-5.0) == 0.0


def test_emission_factors_sane():
    assert KG_CO2_PER_KM["Car (petrol/diesel)"] > KG_CO2_PER_KM["Bus"]
    assert KG_CO2_PER_KM["Bus"] > KG_CO2_PER_KM["Metro"]
    assert KG_CO2_PER_KM["Cycle"] == 0.0
    assert KG_CO2_PER_KM["Walk"] == 0.0


def test_swaps_for_puts_tailored_first():
    swaps = swaps_for("Car (petrol/diesel)", 10.0)
    assert swaps[0].category == "Transport"
    assert "metro or bus" in swaps[0].action
    assert len(swaps) == len(ALL_SWAPS) + 1


def test_swaps_for_work_from_home_has_no_tailored():
    swaps = swaps_for("Work from home", 0.0)
    assert len(swaps) == len(ALL_SWAPS)


def test_all_swaps_have_category_action_impact():
    assert len(ALL_SWAPS) == 13
    categories = {s.category for s in ALL_SWAPS}
    assert categories == {"Transport", "Home", "Food", "Shopping"}
    for swap in ALL_SWAPS:
        assert swap.title.strip()
        assert swap.action.strip()
        assert swap.impact.strip()
