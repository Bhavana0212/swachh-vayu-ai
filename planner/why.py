"""Signature feature: "Why This, Why Now?" — the shared explanation component.

EVERY recommendation in the app shows three lines:
* Why this? — why this suggestion was given.
* Why now? — why this timing is better given today's AQI + forecast.
* What impact? — expected effect on exposure or emissions.

This module is the single shared implementation: logic modules build
WhyNow objects, the UI renders them with why_block_html(), and exports use
why_block_markdown(). No recommendation renders one-off explanation text.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WhyNow:
    """The three-line explanation attached to a recommendation."""

    why_this: str
    why_now: str
    what_impact: str

    def is_complete(self) -> bool:
        """True when all three lines are non-empty."""
        return bool(self.why_this.strip() and self.why_now.strip()
                    and self.what_impact.strip())


def why_block_html(why: WhyNow) -> str:
    """Render the three lines as an accessible HTML block."""
    return (
        '<div class="impact-note" role="note" aria-label="Why this recommendation">'
        f"<b>Why this?</b> {why.why_this}<br>"
        f"<b>Why now?</b> {why.why_now}<br>"
        f"<b>What impact?</b> {why.what_impact}</div>"
    )


def why_block_markdown(why: WhyNow) -> str:
    """Render the three lines as Markdown (for exports)."""
    return (
        f"- **Why this?** {why.why_this}\n"
        f"- **Why now?** {why.why_now}\n"
        f"- **What impact?** {why.what_impact}"
    )


def why_now_for_aqi(aqi: float | None) -> str:
    """Shared 'Why now?' line for non-timed suggestions, from today's AQI."""
    if aqi is None:
        return ("No current reading is available, so the cautious choice is "
                "to act now and check again later.")
    if aqi > 200:
        return ("Today's air is very poor, so every avoided trip and every "
                "indoor action counts more than usual.")
    if aqi > 100:
        return ("Today's air is unhealthy for sensitive groups, so small "
                "changes to timing and travel add up.")
    if aqi > 50:
        return ("Today's air is moderate — a good day to build the habit "
                "before the next poor-air day.")
    return ("Today's air is good, so this is the easiest day to start the "
            "habit and keep it going.")
