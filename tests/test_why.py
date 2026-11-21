"""Signature feature: every recommendation carries Why This / Why Now /
What Impact."""
from planner.routine import build_day_plan
from planner.why import WhyNow, why_block_html, why_block_markdown


def test_whynow_fields():
    why = WhyNow(why_this="A", why_now="B", what_impact="C")
    assert why.why_this == "A"
    assert why.why_now == "B"
    assert why.what_impact == "C"


def test_why_block_html_has_all_three_lines():
    html = why_block_html(WhyNow("A", "B", "C"))
    assert "Why this?" in html
    assert "Why now?" in html
    assert "What impact?" in html
    assert "A" in html and "B" in html and "C" in html


def test_why_block_markdown_has_all_three_lines():
    md = why_block_markdown(WhyNow("A", "B", "C"))
    assert "Why this?" in md
    assert "Why now?" in md
    assert "What impact?" in md


def test_every_plan_item_has_complete_why(profile, report):
    plan = build_day_plan(profile, report)
    assert len(plan.items) >= 6
    for item in plan.items:
        why = item.why_or_default()
        assert why.why_this.strip()
        assert why.why_now.strip()
        assert why.what_impact.strip()
