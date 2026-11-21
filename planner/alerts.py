"""In-app smart alerts (no push notifications).

Alerts are computed from the current modelled estimate and the user's
profile each time the dashboard loads. They are shown in the app only —
nothing is sent anywhere.
"""
from __future__ import annotations

from dataclasses import dataclass

from .api import AirReport
from .routine import Profile
from .utils import hour_label


@dataclass
class Alert:
    """One in-app alert."""

    severity: str  # "info" | "warning" | "critical"
    title: str
    message: str
    action: str


def build_alerts(report: AirReport, profile: Profile) -> list[Alert]:
    """Build the alert list for today's conditions."""
    alerts: list[Alert] = []
    current = report.current
    aqi, scale, category = report.primary_aqi()
    indian = scale.startswith("Indian")
    guidance = ("Poor air — limit outdoor exertion and wear a mask for "
                "essential trips." if aqi is not None
                and aqi > (200 if indian else 150) else
                "Outdoor time is fine — prefer quieter streets.")

    # Daily summary — always present.
    if aqi is not None:
        alerts.append(Alert(
            severity="info",
            title=(f"Today in {report.city.name}: {scale} {aqi:g} "
                   f"({category})"),
            message=guidance,
            action="See My Routine for your tailored plan for today.",
        ))
    else:
        alerts.append(Alert(
            severity="warning",
            title="No current AQI reading",
            message=("The latest modelled estimate is unavailable right now, "
                     "so the app is showing sample values."),
            action="Check again later; keep outdoor time short meanwhile.",
        ))

    # Poor-AQI alert.
    poor_limit = 200 if indian else 150
    if aqi is not None and aqi > poor_limit:
        alerts.append(Alert(
            severity=("critical" if aqi > (300 if indian else 200)
                      else "warning"),
            title="Poor air today — limit outdoor exertion",
            message=(f"{scale} {aqi:g} ({category}) in {report.city.name}. "
                     "Sensitive groups should stay indoors as much as "
                     "possible."),
            action="Wear a well-fitting N95/FFP2 mask for essential trips.",
        ))

    # High PM2.5 alert.
    if current.pm2_5 is not None and current.pm2_5 > 55.0:
        alerts.append(Alert(
            severity="warning",
            title=f"High PM2.5: {current.pm2_5:.0f} µg/m³",
            message=("Fine particles are elevated — the main driver of "
                     "today's health risk."),
            action="Keep windows closed and run the purifier indoors.",
        ))

    # Outdoor-activity warning for the user's profile.
    limit = profile.exercise_limit(indian=indian)
    if aqi is not None and aqi > limit:
        alerts.append(Alert(
            severity="warning",
            title="Outdoor exercise above your limit",
            message=(f"{scale} {aqi:g} is above your {limit} "
                     f"limit for {profile.sensitivity.lower()}."),
            action="Exercise indoors today, or use the Activity Planner to "
                   "find the cleanest window.",
        ))

    # Ventilation tip from the forecast.
    best = report.best_hour_today()
    if best is not None and best.primary_aqi is not None and aqi is not None \
            and best.primary_aqi < aqi:
        alerts.append(Alert(
            severity="info",
            title=f"Best time to air out: {hour_label(best.time)}",
            message=(f"The cleanest hour today is {hour_label(best.time)} "
                     f"({scale} {best.primary_aqi:g})."),
            action="Open windows for 20–30 minutes then, and close up again.",
        ))
    return alerts
