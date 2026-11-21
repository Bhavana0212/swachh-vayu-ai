"""Household Personalization: family profiles, one household, different
recommendations per member.

Roles: General adult, Child, Senior citizen, Athlete, Asthma / respiratory
condition. Guidance is conservative and NON-diagnostic — it adapts the
same public AQI guidance to each member's sensitivity, and never diagnoses
or prescribes.
"""
from __future__ import annotations

from dataclasses import dataclass

from .api import AirReport

ROLES = ["General adult", "Child", "Senior citizen", "Athlete",
         "Asthma / respiratory condition"]

# Per-role limits: (exercise limit, mask limit). Indian limits follow CPCB
# bands (Moderate tops at 200, Satisfactory at 100); US limits follow EPA.
ROLE_LIMITS_INDIAN: dict[str, tuple[int, int]] = {
    "General adult": (200, 200),
    "Child": (100, 100),
    "Senior citizen": (100, 100),
    "Athlete": (200, 200),
    "Asthma / respiratory condition": (100, 100),
}
ROLE_LIMITS_US: dict[str, tuple[int, int]] = {
    "General adult": (150, 150),
    "Child": (100, 100),
    "Senior citizen": (100, 100),
    "Athlete": (150, 150),
    "Asthma / respiratory condition": (100, 100),
}
ROLE_LIMITS = ROLE_LIMITS_INDIAN

ROLE_NOTES: dict[str, str] = {
    "General adult": "Standard public guidance applies.",
    "Child": "Children breathe faster and spend more time outdoors — keep "
             "long outdoor play short on poor-air days.",
    "Senior citizen": "Older adults are more affected by particle pollution "
                      "— prefer indoor activity on poor-air days.",
    "Athlete": "Hard training means deep, fast breathing — time sessions to "
               "the cleanest window.",
    "Asthma / respiratory condition": "Follow your clinician's plan; keep "
                                      "reliever medication handy and avoid "
                                      "known triggers.",
}


@dataclass
class Member:
    """One household member."""

    name: str
    role: str = "General adult"

    def exercise_limit(self, indian: bool = True) -> int:
        table = ROLE_LIMITS_INDIAN if indian else ROLE_LIMITS_US
        return table.get(self.role, (200, 200) if indian else (150, 150))[0]

    def mask_limit(self, indian: bool = True) -> int:
        table = ROLE_LIMITS_INDIAN if indian else ROLE_LIMITS_US
        return table.get(self.role, (200, 200) if indian else (150, 150))[1]


@dataclass
class MemberGuidance:
    """Today's guidance for one member."""

    member: Member
    aqi_now: float | None
    category: str
    outdoor_verdict: str
    guidance: str


def member_guidance(member: Member, report: AirReport) -> MemberGuidance:
    """Conservative, non-diagnostic guidance for one member today."""
    aqi, _scale, category = report.primary_aqi()
    indian = _scale.startswith("Indian")
    if aqi is None:
        return MemberGuidance(
            member=member, aqi_now=None, category="Unavailable",
            outdoor_verdict="Check later",
            guidance=("No current reading is available — keep outdoor time "
                      "short until data returns. " + ROLE_NOTES[member.role]))
    if aqi > member.exercise_limit(indian=indian):
        verdict = "Stay indoors"
        guidance = (f"AQI {aqi:g} is above {member.name}'s limit of "
                    f"{member.exercise_limit(indian=indian)}. Keep activity "
                    "indoors today and wear a mask for essential trips. "
                    + ROLE_NOTES[member.role])
    elif aqi > member.mask_limit(indian=indian):
        verdict = "Short outings, mask on"
        guidance = (f"AQI {aqi:g} is above the mask limit for {member.name}. "
                    "Short outings are fine with a well-fitting N95/FFP2 "
                    "mask. " + ROLE_NOTES[member.role])
    else:
        verdict = "Outdoor time is fine"
        guidance = (f"AQI {aqi:g} is within {member.name}'s limit. Outdoor "
                    "time is fine — prefer quieter streets. "
                    + ROLE_NOTES[member.role])
    return MemberGuidance(member=member, aqi_now=aqi,
                          category=category, outdoor_verdict=verdict,
                          guidance=guidance)


def household_summary(members: list[Member],
                      report: AirReport) -> list[MemberGuidance]:
    """Guidance for every member of the household."""
    return [member_guidance(member, report) for member in members]
