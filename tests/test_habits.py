"""Habit tracker, streaks, badges, challenge and goals."""
from datetime import date, timedelta

import pytest

from planner.habits import (
    HABITS,
    badges_earned,
    challenge_progress,
    days_active,
    goal_progress,
    habits_this_week,
    log_habit,
    streak_days,
    total_habits,
    weekly_report_text,
)


def test_habits_list_nonempty():
    assert len(HABITS) >= 5
    assert all(h.strip() for h in HABITS)


def test_log_habit_adds_and_dedupes():
    log: dict[str, list[str]] = {}
    log = log_habit(log, "2026-11-21", HABITS[0])
    log = log_habit(log, "2026-11-21", HABITS[0])
    assert total_habits(log) == 1
    log = log_habit(log, "2026-11-21", HABITS[1])
    assert total_habits(log) == 2


def test_streak_counts_consecutive_days():
    today = date(2026, 11, 21)
    log = {}
    for i in range(3):
        day = (today - timedelta(days=i)).isoformat()
        log = log_habit(log, day, HABITS[0])
    assert streak_days(log, today) == 3
    assert days_active(log) == 3


def test_streak_breaks_on_gap():
    today = date(2026, 11, 21)
    log = {}
    log = log_habit(log, today.isoformat(), HABITS[0])
    log = log_habit(log, (today - timedelta(days=2)).isoformat(), HABITS[0])
    assert streak_days(log, today) == 1


def test_badges_earned_progression():
    log: dict[str, list[str]] = {}
    badges = dict((name, earned) for name, _, earned in badges_earned(log))
    assert badges["First step"] is False
    log = log_habit(log, "2026-11-21", HABITS[0])
    badges = dict((name, earned) for name, _, earned in badges_earned(log))
    assert badges["First step"] is True
    assert badges["Clean-air champion"] is False


def test_challenge_progress():
    progress = challenge_progress([1, 2, 3])
    assert progress["days_done"] == 3
    assert progress["days_total"] == 7
    assert progress["percent"] == 43
    assert progress["complete"] is False
    assert progress["next_day"] == 4
    full = challenge_progress([1, 2, 3, 4, 5, 6, 7])
    assert full["complete"] is True
    assert full["percent"] == 100


def test_goal_progress_percentage():
    assert goal_progress(10.0, 5.0) == 50.0
    assert goal_progress(10.0, 12.0) == 120.0
    assert goal_progress(0.0, 5.0) == 0.0


def test_habits_this_week_counts_recent():
    today = date.today()
    log = {}
    log = log_habit(log, today.isoformat(), HABITS[0])
    log = log_habit(log, (today - timedelta(days=10)).isoformat(), HABITS[0])
    assert habits_this_week(log) == 1


def test_weekly_report_text():
    log = {}
    log = log_habit(log, "2026-11-21", HABITS[0])
    text = weekly_report_text(log, "Week of 2026-11-16")
    assert "Week of 2026-11-16" in text
    assert "Habits logged: 1" in text
