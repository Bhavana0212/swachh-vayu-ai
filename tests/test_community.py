"""Community: report generation, quiz, household leaderboard."""
from planner.community import (
    COMMUNITY_CHALLENGES,
    QUIZ_QUESTIONS,
    PollutionReport,
    grade_quiz,
    household_leaderboard,
)


def test_pollution_report_formatted_contains_fields():
    report = PollutionReport(
        report_type="Visible smoke / garbage burning",
        location="Near City Mall", city="Delhi", date="2026-11-21",
        description="Garbage burning every evening.", reporter="Asha")
    text = report.formatted()
    assert "Visible smoke" in text
    assert "Near City Mall" in text
    assert "Delhi" in text
    assert "2026-11-21" in text
    assert "Garbage burning every evening." in text
    assert "Asha" in text
    assert "does NOT submit" in text


def test_pollution_report_without_reporter():
    report = PollutionReport(
        report_type="Other", location="X", city="Delhi",
        date="2026-11-21", description="")
    text = report.formatted()
    assert "Reported by" not in text
    assert "No description given" in text


def test_community_challenges_nonempty():
    assert len(COMMUNITY_CHALLENGES) >= 4
    assert all(title.strip() and desc.strip()
               for title, desc in COMMUNITY_CHALLENGES)


def test_quiz_all_correct():
    answers = {i: q["answer"] for i, q in enumerate(QUIZ_QUESTIONS)}
    correct, total, explanations = grade_quiz(answers)
    assert correct == total == len(QUIZ_QUESTIONS)
    assert all("Correct" in e for e in explanations)


def test_quiz_all_wrong():
    answers = {i: (q["answer"] + 1) % len(q["options"])
               for i, q in enumerate(QUIZ_QUESTIONS)}
    correct, total, explanations = grade_quiz(answers)
    assert correct == 0
    assert total == len(QUIZ_QUESTIONS)


def test_quiz_partial_answers():
    correct, total, _ = grade_quiz({})
    assert correct == 0
    assert total == len(QUIZ_QUESTIONS)


def test_household_leaderboard_ranks_descending():
    ranked = household_leaderboard({"Asha": 40, "Ravi": 60, "Meera": 40})
    assert ranked[0] == (1, "Ravi", 60)
    assert ranked[1][2] == 40
    assert ranked[2][2] == 40
    assert [r[0] for r in ranked] == [1, 2, 3]
