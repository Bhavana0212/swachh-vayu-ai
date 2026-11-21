"""Markdown and CSV export of the day plan."""
import csv
import io

from planner.export import plan_to_csv, plan_to_markdown
from planner.routine import build_day_plan


def _plan(profile, report):
    return build_day_plan(profile, report)


def test_markdown_has_title_city_and_aqi(profile, report):
    md = plan_to_markdown(profile, report, _plan(profile, report))
    assert md.startswith("# My Air Quality Plan — Delhi")
    assert "268" in md  # calculated Indian AQI (primary)
    assert "Poor" in md
    assert "Indian AQI (CPCB)" in md
    assert "Open-Meteo" in md


def test_markdown_lists_all_items(profile, report):
    plan = _plan(profile, report)
    md = plan_to_markdown(profile, report, plan)
    for item in plan.items:
        assert item.title in md
        assert item.action in md
        why = item.why_or_default()
        assert why.why_this in md
        assert why.why_now in md
        assert why.what_impact in md


def test_markdown_has_disclaimer(profile, report):
    md = plan_to_markdown(profile, report, _plan(profile, report))
    assert "not medical advice" in md


def test_markdown_includes_profile(profile, report):
    md = plan_to_markdown(profile, report, _plan(profile, report))
    assert "General" in md
    assert "Metro" in md


def test_csv_has_header_and_rows(profile, report):
    plan = _plan(profile, report)
    text = plan_to_csv(profile, report, plan)
    rows = list(csv.reader(io.StringIO(text)))
    assert rows[0] == ["city", "date", "aqi_primary", "aqi_scale",
                       "category", "sensitivity", "item", "window", "action",
                       "why_this", "why_now", "what_impact"]
    assert len(rows) == len(plan.items) + 1
    assert all(row[0] == "Delhi" for row in rows[1:])
    assert all(row[2] in ("268", "268.0") for row in rows[1:])
    assert all(row[3] == "Indian AQI (CPCB)" for row in rows[1:])


def test_csv_handles_missing_aqi(profile, report):
    from planner.indian_aqi import IndianAQI
    report.current.us_aqi = None
    report.indian_aqi = IndianAQI(
        value=None, category="Unavailable", colour="#E5E7EB",
        text_colour="#1A1A1A", symbol="?", dominant="none",
        available=False, reason="Insufficient data for Indian AQI.")
    plan = _plan(profile, report)
    rows = list(csv.reader(io.StringIO(plan_to_csv(profile, report, plan))))
    assert rows[1][2] == ""


def test_pdf_returns_valid_bytes(profile, report):
    from planner.export import plan_to_pdf
    data = plan_to_pdf(profile, report, _plan(profile, report))
    assert data.startswith(b"%PDF")
    assert len(data) > 500


def test_share_summary_mentions_city_and_score(profile, report):
    from planner.export import share_summary
    text = share_summary(profile, report, _plan(profile, report),
                         impact_score_total=72)
    assert "Delhi" in text
    assert "72/100" in text
    assert "SwachhVayu AI" in text
