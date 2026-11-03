"""Streaks: runs of consecutive periods in which a habit was done often enough.

Because schedule.py numbers periods consecutively (scheduled days, or weeks), "consecutive"
just means "consecutive integers". `itertools.groupby` finds those runs with the classic
value-minus-index trick: in 3, 4, 5, 9, 10 the differences from their positions are
3, 3, 3, 6, 6, and each distinct difference is one run.
"""

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from itertools import groupby

from .log import Habit


@dataclass(frozen=True, slots=True)
class Streak:
    current: int
    longest: int
    unit: str  # "day" or "week"
    at_risk: bool  # alive, but this period isn't done yet: do it today (or this week)

    def label(self, n: int) -> str:
        return f"{n} {self.unit}{'' if n == 1 else 's'}"


def runs(periods: Iterable[int]) -> list[range]:
    """Group sorted, distinct ints into runs: `[3, 4, 5, 9, 10]` → `[range(3, 6), range(9, 11)]`."""
    found = []
    for _, group in groupby(enumerate(periods), key=lambda pair: pair[1] - pair[0]):
        members = [period for _, period in group]
        found.append(range(members[0], members[-1] + 1))
    return found


def counts(habit: Habit, days: Iterable[date]) -> Counter[int]:
    """How many check-ins fell in each period. Days the schedule doesn't cover are ignored."""
    return Counter(p for d in days if (p := habit.schedule.period(d)) is not None)


def streak(habit: Habit, days: set[date], today: date) -> Streak:
    schedule = habit.schedule
    per_period = counts(habit, (d for d in days if d <= today))
    met = sorted(p for p, n in per_period.items() if n >= schedule.need)
    found = runs(met)
    longest = max(map(len, found), default=0)

    now = schedule.latest(today)  # the period that ends a live streak
    still_open = schedule.period(today) == now  # today is part of it, so it isn't over yet
    current, at_risk = 0, False
    if found and found[-1][-1] == now:
        current = len(found[-1])
    elif found and found[-1][-1] == now - 1 and still_open:
        current, at_risk = len(found[-1]), True
    return Streak(current, longest, schedule.unit, at_risk)


def progress(habit: Habit, days: set[date], today: date) -> tuple[int, int]:
    """(check-ins, needed) for the period containing `today`, or the last scheduled one."""
    now = habit.schedule.latest(today)
    return counts(habit, days)[now], habit.schedule.need
