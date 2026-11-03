from datetime import date, timedelta

import pytest

from py_habit_tracker.log import Habit
from py_habit_tracker.schedule import parse_schedule
from py_habit_tracker.streaks import Streak, runs, streak

TUESDAY = date(2026, 11, 3)


def habit(schedule: str) -> Habit:
    return Habit("test", parse_schedule(schedule), date(2026, 1, 1))


def back(*offsets: int) -> set[date]:
    """Days counted back from TUESDAY: back(0, 1) is today and yesterday."""
    return {TUESDAY - timedelta(days=n) for n in offsets}


@pytest.mark.parametrize(
    ("periods", "expected"),
    [
        ([], []),
        ([7], [range(7, 8)]),
        ([3, 4, 5, 9, 10], [range(3, 6), range(9, 11)]),
        ([1, 3, 5], [range(1, 2), range(3, 4), range(5, 6)]),
    ],
)
def test_runs_groups_consecutive_integers(periods: list[int], expected: list[range]) -> None:
    assert runs(periods) == expected


@pytest.mark.parametrize(
    ("days", "expected"),
    [
        (back(0, 1, 2), Streak(3, 3, "day", at_risk=False)),
        (back(1, 2), Streak(2, 2, "day", at_risk=True)),  # today isn't over: still alive
        (back(2, 3, 4, 5, 9), Streak(0, 4, "day", at_risk=False)),  # yesterday was missed
        (back(0, 5, 6, 7, 8, 9), Streak(1, 5, "day", at_risk=False)),
        (set(), Streak(0, 0, "day", at_risk=False)),
    ],
)
def test_daily_streaks(days: set[date], expected: Streak) -> None:
    assert streak(habit("daily"), days, TUESDAY) == expected


def test_days_off_the_schedule_neither_break_nor_extend_a_streak() -> None:
    # Weekdays Mon 26 Oct - Tue 3 Nov, plus a run on Sunday: the weekend doesn't count.
    days = back(0, 1, 4, 5, 6, 7, 8) | back(2)
    assert streak(habit("weekdays"), days, TUESDAY) == Streak(7, 7, "day", at_risk=False)


def test_weekly_quota_streaks_cross_new_year() -> None:
    gym = habit("2/week")
    # Two sessions in each of four weeks around New Year, then one so far "this week".
    days = {date(2026, 12, 15), date(2026, 12, 17), date(2026, 12, 22), date(2026, 12, 26),
            date(2026, 12, 29), date(2027, 1, 2), date(2027, 1, 5), date(2027, 1, 9),
            date(2027, 1, 12)}  # fmt: skip
    assert streak(gym, days, date(2027, 1, 13)) == Streak(4, 4, "week", at_risk=True)
    # 2026-12-28 to 2027-01-03 is one week, though the ISO calendar calls it 2026-W53.
    assert date(2026, 12, 29).isocalendar()[:2] == (2026, 53)
    assert date(2027, 1, 2).isocalendar()[:2] == (2026, 53)
