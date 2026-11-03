"""When a habit is due: on certain weekdays, or a number of times per week.

A schedule cuts time into numbered *periods*. For `OnDays` a period is one scheduled day; for
`PerWeek` it is one Monday-to-Sunday week. Consecutive periods get consecutive numbers, so a
streak is simply a run of consecutive integers, whatever the schedule (see streaks.py).

The numbers come from `date.toordinal()`: day 1 is 0001-01-01, which was a Monday, so
`divmod(ordinal - 1, 7)` gives (week number, weekday) with no calendar maths at all.
"""

import re
from dataclasses import dataclass
from datetime import date, timedelta

DAY_NAMES = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")  # index == date.weekday()
_FULL_NAMES = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def week_and_day(d: date) -> tuple[int, int]:
    """`(weeks since 0001-01-01, weekday)`, Monday = 0. Works across years, unlike ISO weeks."""
    return divmod(d.toordinal() - 1, 7)


@dataclass(frozen=True, slots=True)
class OnDays:
    """Due on each of these weekdays (0 = Monday, like `date.weekday()`)."""

    weekdays: frozenset[int]

    unit = "day"
    need = 1

    def period(self, d: date) -> int | None:
        week, weekday = week_and_day(d)
        if weekday not in self.weekdays:
            return None
        order = sorted(self.weekdays)
        return week * len(order) + order.index(weekday)

    def latest(self, today: date) -> int:
        """The period of the last scheduled day on or before `today`."""
        back = (today - timedelta(days=n) for n in range(7))
        return next(p for d in back if (p := self.period(d)) is not None)


@dataclass(frozen=True, slots=True)
class PerWeek:
    """Due `times` times in each Monday-to-Sunday week, on any days."""

    times: int

    unit = "week"

    @property
    def need(self) -> int:
        return self.times

    def period(self, d: date) -> int:
        return week_and_day(d)[0]

    def latest(self, today: date) -> int:
        return self.period(today)


type Schedule = OnDays | PerWeek

_PER_WEEK = re.compile(r"(?P<n>[1-7])\s*(?:x|/|times?)\s*(?:a\s*)?(?:w|wk|week)")


def parse_schedule(text: str) -> Schedule:
    """`daily`, `weekdays`, `weekends`, `mon,wed,fri` or `3/week` (also `3x week`)."""
    spec = text.strip().lower()
    match spec:
        case "daily" | "every day" | "everyday":
            return OnDays(frozenset(range(7)))
        case "weekdays":
            return OnDays(frozenset(range(5)))
        case "weekends":
            return OnDays(frozenset({5, 6}))
        case _ if m := _PER_WEEK.fullmatch(spec):
            return PerWeek(int(m["n"]))
    days = frozenset(day_number(word) for word in re.split(r"[\s,]+", spec) if word)
    if not days:
        raise ValueError("a schedule needs at least one day")
    return OnDays(days)


def day_number(word: str) -> int:
    """`"mon"`, `"mo"` or `"monday"` → 0. A prefix has to pick out exactly one day."""
    found = [n for n, name in enumerate(_FULL_NAMES) if len(word) >= 2 and name.startswith(word)]
    if len(found) != 1:
        raise ValueError(
            f"can't read schedule word {word!r}: use daily, weekdays, weekends, "
            "day names like mon,wed,fri, or a count like 3/week"
        )
    return found[0]


def spec(schedule: Schedule) -> str:
    """The canonical text for a schedule; `parse_schedule(spec(s)) == s`."""
    match schedule:
        case OnDays(weekdays=days) if days == frozenset(range(7)):
            return "daily"
        case OnDays(weekdays=days) if days == frozenset(range(5)):
            return "weekdays"
        case OnDays(weekdays=days) if days == frozenset({5, 6}):
            return "weekends"
        case OnDays(weekdays=days):
            return ",".join(DAY_NAMES[d] for d in sorted(days))
        case PerWeek(times=n):
            return f"{n}/week"
