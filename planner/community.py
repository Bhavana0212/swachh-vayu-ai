"""Community & Education: local pollution reporting, community
challenges, school/college awareness mode and the household leaderboard.

Honesty rules: Report Local Pollution GENERATES a formatted report the
user can send to local authorities — the app does NOT submit anything.
The leaderboard is household-local only (members of this session) —
never a fake global leaderboard. Community challenges are tracked
locally in the session/store.
"""
from __future__ import annotations

from dataclasses import dataclass

REPORT_TYPES = [
    "Visible smoke / garbage burning",
    "Construction dust (uncovered site)",
    "Road dust / unpaved road",
    "Industrial smoke",
    "Burning of leaves / waste",
    "Other",
]

REPORT_DISCLAIMER = ("This report is generated for you to send to your "
                     "local authority (municipal corporation, pollution "
                     "control board, or the CPCB Sameer app). SwachhVayu "
                     "AI does NOT submit it anywhere.")


@dataclass
class PollutionReport:
    """A formatted local-pollution report (generated, not submitted)."""

    report_type: str
    location: str
    city: str
    date: str
    description: str
    reporter: str = ""

    def formatted(self) -> str:
        """The report as plain text the user can copy or download."""
        lines = [
            "LOCAL POLLUTION REPORT",
            "======================",
            f"Type: {self.report_type}",
            f"Location: {self.location}",
            f"City: {self.city}",
            f"Date observed: {self.date}",
        ]
        if self.reporter:
            lines.append(f"Reported by: {self.reporter}")
        lines.append("")
        lines.append("Description:")
        lines.append(self.description or "(No description given.)")
        lines.append("")
        lines.append(
            "Suggested next step: share this report with your municipal "
            "corporation, the State Pollution Control Board, or through "
            "the CPCB Sameer app.")
        lines.append("")
        lines.append(REPORT_DISCLAIMER)
        return "\n".join(lines)


COMMUNITY_CHALLENGES = [
    ("Neighbourhood walking week",
     "Walk for every trip under 1 km this week — log each walk in the "
     "habit tracker."),
    ("Public transport week",
     "Take the metro or bus for every commute this week."),
    ("No-burn week",
     "No garbage or leaf burning in your lane — talk to neighbours and "
     "report burning through the report tool."),
    ("Waste reduction week",
     "Segregate waste daily and carry a cloth bag for every shop visit."),
    ("Clean-air Sunday",
     "One car-free Sunday for the household — walk, cycle or stay local."),
]

QUIZ_QUESTIONS: list[dict] = [
    {
        "question": "What does AQI stand for?",
        "options": ["Air Quality Index", "Air Quantity Indicator",
                    "Atmospheric Quality Instrument"],
        "answer": 0,
        "explain": ("AQI is the Air Quality Index — a single number that "
                    "summarises how clean or polluted the air is."),
    },
    {
        "question": "Which particle is small enough to reach deep into the lungs?",
        "options": ["PM10", "PM2.5", "Dust you can see"],
        "answer": 1,
        "explain": ("PM2.5 particles are under 2.5 micrometres — small "
                    "enough to pass deep into the lungs and even the "
                    "bloodstream."),
    },
    {
        "question": "When is the air usually cleanest in an Indian city?",
        "options": ["8 AM rush hour", "Mid-afternoon",
                    "8 PM rush hour"],
        "answer": 1,
        "explain": ("Mid-afternoon usually has the best dispersion — the "
                    "sun has warmed the air and traffic is lighter. "
                    "Check the dashboard's cleanest-hour figure for today."),
    },
    {
        "question": "Which mask filters most PM2.5?",
        "options": ["Cloth mask", "Surgical mask",
                    "Well-fitting N95 / FFP2 mask"],
        "answer": 2,
        "explain": ("Only a well-fitting N95/FFP2 respirator filters most "
                    "fine particles — and the seal matters as much as the "
                    "filter."),
    },
    {
        "question": "What is the biggest indoor particle source in most homes?",
        "options": ["Houseplants", "Cooking smoke", "Books"],
        "answer": 1,
        "explain": ("Cooking — especially frying and high-heat tadka — "
                    "releases more indoor PM2.5 than any other everyday "
                    "source. Use the chimney every time."),
    },
    {
        "question": "Why can two apps show different AQI numbers for the same city?",
        "options": ["One of them is broken",
                    "They use different scales (Indian, US, European) and "
                    "different data (station vs modelled)",
                    "AQI changes every second"],
        "answer": 1,
        "explain": ("Indian (CPCB), US (EPA) and European scales use "
                    "different bands and averaging — and some apps use "
                    "station readings while others use modelled data. "
                    "SwachhVayu AI shows all three, labelled."),
    },
]


def grade_quiz(answers: dict[int, int]) -> tuple[int, int, list[str]]:
    """Grade quiz answers: (correct, total, per-question explanations)."""
    correct = 0
    explanations = []
    for i, question in enumerate(QUIZ_QUESTIONS):
        chosen = answers.get(i)
        if chosen == question["answer"]:
            correct += 1
            explanations.append(f"Q{i + 1}: Correct. {question['explain']}")
        else:
            explanations.append(
                f"Q{i + 1}: The answer is "
                f"'{question['options'][question['answer']]}'. "
                f"{question['explain']}")
    return correct, len(QUIZ_QUESTIONS), explanations


def household_leaderboard(scores: dict[str, int]) -> list[tuple[int, str, int]]:
    """Rank household members by score (household-local only).

    Returns [(rank, name, score)] sorted by score descending.
    """
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return [(i + 1, name, score) for i, (name, score) in enumerate(ranked)]
