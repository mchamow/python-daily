from datetime import date, timedelta

import pytest

from py_habit_tracker.log import parse_day
from py_habit_tracker.schedule import OnDays, PerWeek, Schedule, parse_schedule, spec

TUESDAY = date(2026, 11, 3)


@pytest.mark.parametrize(
    ("text", "schedule", "canonical"),
    [
        ("daily", OnDays(frozenset(range(7))), "daily"),
        ("Weekdays", OnDays(frozenset(range(5))), "weekdays"),
        ("sa,su", OnDays(frozenset({5, 6})), "weekends"),
        ("Friday, monday wed", OnDays(frozenset({0, 2, 4})), "mon,wed,fri"),
        ("3x week", PerWeek(3), "3/week"),
        ("2 times a week", PerWeek(2), "2/week"),
    ],
)
def test_parse_schedule_and_its_canonical_spelling(
    text: str, schedule: Schedule, canonical: str
) -> None:
    assert parse_schedule(text) == schedule
    assert spec(schedule) == canonical
    assert parse_schedule(canonical) == schedule  # what the log file stores reads back


@pytest.mark.parametrize("text", ["sometimes", "s,mon", "8/week", ","])
def test_parse_schedule_rejects_nonsense(text: str) -> None:
    with pytest.raises(ValueError):
        parse_schedule(text)


def test_scheduled_days_are_numbered_consecutively_across_weeks_and_years() -> None:
    mwf = parse_schedule("mon,wed,fri")
    days = [date(2026, 12, 21) + timedelta(days=n) for n in range(21)]  # into 2027
    periods = [p for d in days if (p := mwf.period(d)) is not None]
    assert len(periods) == 9
    assert periods == list(range(periods[0], periods[0] + 9))  # no gaps at weekends or New Year


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("today", TUESDAY),
        ("yesterday", date(2026, 11, 2)),
        ("-7", date(2026, 10, 27)),
        ("tue", TUESDAY),  # the most recent Tuesday is today
        ("wednesday", date(2026, 10, 28)),  # looking back, not forward (Day 4 looked forward)
        ("2026-02-28", date(2026, 2, 28)),
    ],
)
def test_parse_day(text: str, expected: date) -> None:
    assert parse_day(text, TUESDAY) == expected


@pytest.mark.parametrize("text", ["tomorrow", "2026-11-04", "2026-02-30", "soon"])
def test_parse_day_rejects_the_future_and_nonsense(text: str) -> None:
    with pytest.raises(ValueError):
        parse_day(text, TUESDAY)
