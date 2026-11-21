"""Export the day's plan and impact report: Markdown, CSV, PDF, share text.

Single-session, no account. PDF uses reportlab (free, open source).
"""
from __future__ import annotations

import csv
import io
from datetime import date

from .api import AirReport
from .routine import DayPlan, Profile
from .why import why_block_markdown


def plan_to_markdown(profile: Profile, report: AirReport,
                     plan: DayPlan) -> str:
    """Render the plan as a readable Markdown document."""
    aqi, scale, _category = report.primary_aqi()
    lines = [
        f"# My Air Quality Plan — {report.city.name}",
        "",
        f"**Date:** {date.today().isoformat()}  ",
        f"**City:** {report.city.name}, {report.city.country}  ",
        f"**Current {scale}:** "
        f"{aqi:g} ({plan.category})" if aqi is not None else f"**Current {scale}:** unavailable",
        f"**Source:** {report.source}",
        "",
        f"**Profile:** {profile.sensitivity}; commute {profile.commute_mode} "
        f"({profile.commute_km:g} km); "
        f"exercises {'outdoors' if profile.exercises_outdoors else 'indoors'}; "
        f"purifier: {'yes' if profile.has_purifier else 'no'}",
        "",
        "## Today's plan",
        "",
    ]
    for item in plan.items:
        window = f" — {item.window}" if item.window else ""
        lines.append(f"### {item.title}{window}")
        lines.append("")
        lines.append(item.action)
        lines.append("")
        lines.append(why_block_markdown(item.why_or_default()))
        lines.append("")
    if plan.checklist:
        lines.append("## Today's sustainability checklist")
        lines.append("")
        for entry in plan.checklist:
            lines.append(f"- [ ] {entry}")
        lines.append("")
    lines.append(
        "_General information only, not medical advice. Air data: Open-Meteo "
        "Air Quality API (Copernicus CAMS modelled data — latest available "
        "modelled estimate, not live sensor data)._")
    lines.append("")
    return "\n".join(lines)


def plan_to_csv(profile: Profile, report: AirReport, plan: DayPlan) -> str:
    """Render the plan as CSV: one row per recommendation."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["city", "date", "aqi_primary", "aqi_scale", "category", "sensitivity",
                     "item", "window", "action", "why_this", "why_now",
                     "what_impact"])
    for item in plan.items:
        why = item.why_or_default()
        writer.writerow([
            report.city.name,
            date.today().isoformat(),
            plan.aqi_now if plan.aqi_now is not None else "",
            report.primary_aqi()[1],
            plan.category,
            profile.sensitivity,
            item.title,
            item.window,
            item.action,
            why.why_this,
            why.why_now,
            why.what_impact,
        ])
    return output.getvalue()


def plan_to_pdf(profile: Profile, report: AirReport, plan: DayPlan) -> bytes:
    """Render the plan as a printable PDF (reportlab)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm,
                            title=f"My Air Quality Plan — {report.city.name}",
                            author="SwachhVayu AI")
    styles = getSampleStyleSheet()
    story = []
    aqi, scale, _category = report.primary_aqi()
    story.append(Paragraph(
        f"My Air Quality Plan — {report.city.name}", styles["Title"]))
    story.append(Paragraph(
        f"Date: {date.today().isoformat()} | City: {report.city.name}, "
        f"{report.city.country} | {scale}: "
        f"{aqi:g} ({plan.category})" if aqi is not None else f"{scale}: unavailable",
        styles["Normal"]))
    story.append(Paragraph(f"Source: {report.source}", styles["Normal"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Today's plan", styles["Heading2"]))
    for item in plan.items:
        story.append(Paragraph(item.title, styles["Heading3"]))
        story.append(Paragraph(item.action, styles["Normal"]))
        why = item.why_or_default()
        story.append(Paragraph(
            f"<b>Why this?</b> {why.why_this}<br/>"
            f"<b>Why now?</b> {why.why_now}<br/>"
            f"<b>What impact?</b> {why.what_impact}", styles["Normal"]))
        story.append(Spacer(1, 6))
    story.append(Paragraph(
        "General information only, not medical advice. Air data: Open-Meteo "
        "Air Quality API (Copernicus CAMS modelled data — latest available "
        "modelled estimate, not live sensor data).", styles["Normal"]))
    doc.build(story)
    return buffer.getvalue()


def share_summary(profile: Profile, report: AirReport, plan: DayPlan,
                  impact_score_total: int | None = None) -> str:
    """Shareable plain-text sustainability summary (copy-paste ready)."""
    aqi, scale, _category = report.primary_aqi()
    lines = [
        f"My clean-air plan for {report.city.name} today:",
        f"{scale} {aqi:g} ({plan.category})" if aqi is not None
        else f"{scale} unavailable today",
        f"Commute: {profile.commute_mode} ({profile.commute_km:g} km).",
    ]
    if impact_score_total is not None:
        lines.append(f"My Environmental Impact Score: {impact_score_total}/100.")
    lines.append("Plan built with SwachhVayu AI — free, no login.")
    return "\n".join(lines)
