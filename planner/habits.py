"""Habit tracker, 7-Day Clean Air Challenge, badges, goals, weekly report.

All state lives in the Streamlit session (no login, no account). The log
is a plain dict: {date ISO string: [habit names]}. Functions here are pure
so they can be tested without Streamlit.
"""
from __future__ import annotations

from datetime import date, timedelta

HABITS = [
    "Used public transport or cycled/walked",
    "Ran the purifier in the room I used most",
    "Ventilated at the cleanest hour",
    "Cooked a meat-free meal",
    "Combined errands into one trip",
    "Checked the AQI before going out",
    "Worked from home / skipped a car trip",
]

# 7-Day Clean Air Challenge: day -> (task, why it matters)
CHALLENGE_DAYS: dict[int, tuple[str, str]] = {
    1: ("Check the AQI before you step out",
        "One minute of checking sets the whole day's plan."),
    2: ("Take the lowest-emission commute you can",
        "The commute is the day's biggest single emission."),
    3: ("Ventilate at the cleanest hour",
        "Same fresh air, far less pollution coming in."),
    4: ("Cook one meat-free meal",
        "Plant-based meals carry a much smaller footprint."),
    5: ("Combine all errands into one trip",
        "Fewer cold starts, fewer kilometres, less pollution."),
    6: ("Run the purifier only where you are",
        "Clean air where it matters, less electricity wasted."),
    7: ("Share one clean-air tip with someone",
        "Good habits spread — one shared tip doubles the impact."),
}

# Badges: (name, description, rule) — rule is a function of the log.
BADGES: list[tuple[str, str]] = [
    ("First step", "Logged your first sustainable habit."),
    ("Getting going", "Logged 5 habits in total."),
    ("Clean-air week", "Logged a habit on 7 different days."),
    ("Habit builder", "Logged 25 habits in total."),
    ("Clean-air champion", "Logged 50 habits in total."),
]


def log_habit(log: dict[str, list[str]], day: str,
              habit: str) -> dict[str, list[str]]:
    """Return a new log with `habit` added for `day` (no duplicates)."""
    new_log = {d: list(habits) for d, habits in log.items()}
    if habit not in new_log.get(day, []):
        new_log.setdefault(day, []).append(habit)
    return new_log


def total_habits(log: dict[str, list[str]]) -> int:
    """Total habits logged across all days."""
    return sum(len(habits) for habits in log.values())


def days_active(log: dict[str, list[str]]) -> int:
    """Number of distinct days with at least one habit."""
    return sum(1 for habits in log.values() if habits)


def streak_days(log: dict[str, list[str]], today: date | None = None) -> int:
    """Consecutive days with a habit, ending today (or yesterday if today
    is still empty — the streak is not broken until a day passes)."""
    today = today or date.today()
    streak = 0
    day = today
    if not log.get(day.isoformat()):
        day = today - timedelta(days=1)
    while log.get(day.isoformat()):
        streak += 1
        day -= timedelta(days=1)
    return streak


def habits_this_week(log: dict[str, list[str]],
                     today: date | None = None) -> int:
    """Habits logged in the current calendar week (Mon–Sun)."""
    today = today or date.today()
    monday = today - timedelta(days=today.weekday())
    total = 0
    for i in range(7):
        total += len(log.get((monday + timedelta(days=i)).isoformat(), []))
    return total


def badges_earned(log: dict[str, list[str]]) -> list[tuple[str, str, bool]]:
    """All badges with whether each is earned yet."""
    total = total_habits(log)
    active = days_active(log)
    earned = {
        "First step": total >= 1,
        "Getting going": total >= 5,
        "Clean-air week": active >= 7,
        "Habit builder": total >= 25,
        "Clean-air champion": total >= 50,
    }
    return [(name, desc, earned[name]) for name, desc in BADGES]


def challenge_progress(done_days: list[int]) -> dict[str, float | int | str]:
    """Progress through the 7-day challenge."""
    done = sorted(set(done_days))
    return {
        "days_done": len(done),
        "days_total": 7,
        "percent": round(len(done) / 7 * 100),
        "next_day": next((d for d in range(1, 8) if d not in done), 0),
        "complete": len(done) == 7,
    }


def weekly_report_text(log: dict[str, list[str]],
                       week_label: str) -> str:
    """Plain-text weekly summary of the user's actions."""
    total = total_habits(log)
    active = days_active(log)
    lines = [
        f"Weekly clean-air report — {week_label}",
        f"Habits logged: {total} across {active} day(s).",
        f"Current streak: {streak_days(log)} day(s).",
    ]
    earned = [name for name, _, got in badges_earned(log) if got]
    if earned:
        lines.append("Badges earned: " + ", ".join(earned) + ".")
    else:
        lines.append("Badges earned: none yet — log your first habit!")
    lines.append("Keep going — small daily actions are the whole point.")
    return "\n".join(lines)


def goal_progress(target_kg_per_week: float,
                  estimated_saving_kg_per_week: float) -> float:
    """Progress towards a weekly CO2-saving goal, as a percentage (0-100+)."""
    if target_kg_per_week <= 0:
        return 0.0
    return round(estimated_saving_kg_per_week / target_kg_per_week * 100.0, 1)
