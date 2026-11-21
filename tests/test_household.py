"""Family profiles: per-member guidance from the primary AQI."""
from planner.household import Member, household_summary, member_guidance


def test_member_limits_indian_and_us():
    child = Member(name="Aarav", role="Child")
    assert child.exercise_limit() == 100
    assert child.exercise_limit(indian=False) == 100
    adult = Member(name="Priya", role="General adult")
    assert adult.exercise_limit() == 200
    assert adult.exercise_limit(indian=False) == 150


def test_guidance_stay_indoors_when_above_limit(report):
    # Fixture Indian AQI 268 > 100 for a child.
    guidance = member_guidance(Member(name="Aarav", role="Child"), report)
    assert guidance.outdoor_verdict == "Stay indoors"
    assert guidance.aqi_now == 268
    assert guidance.category == "Poor"


def test_guidance_differs_by_role(report):
    child = member_guidance(Member(name="Aarav", role="Child"), report)
    adult = member_guidance(Member(name="Priya", role="General adult"), report)
    # 268 > 200 adult limit too, so both stay indoors here; check the
    # guidance text differs by role instead.
    assert "Children breathe faster" in child.guidance
    assert "Standard public guidance" in adult.guidance


def test_household_summary_covers_all_members(report):
    members = [Member(name="A", role="Child"),
               Member(name="B", role="Senior citizen")]
    result = household_summary(members, report)
    assert len(result) == 2
    assert result[0].member.name == "A"


def test_guidance_no_data(report):
    from planner.indian_aqi import IndianAQI
    report.current.us_aqi = None
    report.indian_aqi = IndianAQI(
        value=None, category="Unavailable", colour="#E5E7EB",
        text_colour="#1A1A1A", symbol="?", dominant="none",
        available=False, reason="Insufficient data for Indian AQI.")
    guidance = member_guidance(Member(name="A", role="Child"), report)
    assert guidance.outdoor_verdict == "Check later"
    assert guidance.aqi_now is None
