"""Terminal output: the status table, a month calendar and a GitHub-style heatmap.

Colour is plain ANSI SGR escapes (`ESC [ … m`). Everything is rendered in colour, and when
colour is off (NO_COLOR, a pipe, or `--color never`) `plain()` strips the escapes at the very
end. So the glyphs alone still carry the meaning: ● done, · missed, ▢ … █ heatmap levels.
"""

import calendar
import os
import re
from collections.abc import Iterable
from datetime import date, timedelta
from typing import TextIO

from .log import Habit, Log
from .schedule import DAY_NAMES, OnDays, PerWeek, spec
from .streaks import counts, progress, streak

type RGB = tuple[int, int, int]

GREENS: tuple[RGB, ...] = ((45, 51, 59), (14, 68, 41), (0, 109, 50), (38, 166, 65), (57, 211, 83))
LEVEL_GLYPHS = "▢░▒▓█"  # level 0-4, readable without colour
RED: RGB = (218, 54, 51)
YELLOW: RGB = (210, 153, 34)
GREY: RGB = (110, 118, 129)
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def paint(text: str, rgb: RGB | None = None, *, bold: bool = False, under: bool = False) -> str:
    """Wrap `text` in 24-bit colour (`38;2;R;G;B`) and/or bold and underline, then reset."""
    codes = [*(["1"] if bold else []), *(["4"] if under else [])]
    if rgb:
        codes.append("38;2;{};{};{}".format(*rgb))
    return f"\x1b[{';'.join(codes)}m{text}\x1b[0m" if codes else text


def plain(text: str) -> str:
    return ANSI.sub("", text)


def width(text: str) -> int:
    """How many columns `text` takes on screen: escapes take none, though len() counts them."""
    return len(plain(text))


def pad(text: str, size: int) -> str:
    """`f"{text:<{size}}"`, but correct for coloured text."""
    return text + " " * max(size - width(text), 0)


def wants_colour(mode: str, stream: TextIO) -> bool:
    """`auto` follows the https://no-color.org convention, then whether `stream` is a terminal."""
    match mode:
        case "always":
            return True
        case "never":
            return False
        case _:
            return not os.environ.get("NO_COLOR") and stream.isatty()


def _day_cell(habit: Habit, days: set[date], d: date, today: date) -> str:
    """One day for one habit: ● done, · due but missed, blank if not due (or not yet)."""
    if d in days:
        return paint("●", GREENS[4])
    due = isinstance(habit.schedule, OnDays) and habit.schedule.period(d) is not None
    if due and habit.since <= d < today:
        return paint("·", RED)
    return paint("·", GREY) if d == today and due else " "


def status_table(log: Log, today: date, *, days: int = 14) -> str:
    """One row per habit: schedule, this period, current and longest streak, recent days."""
    if not log.habits:
        return "No habits yet. Start one with: habit add run --every daily"
    recent = [today - timedelta(days=n) for n in reversed(range(days))]
    initials = "".join(DAY_NAMES[d.weekday()][0].upper() for d in recent)
    head = ["habit", "schedule", "now", "streak", "best", f"last {days} days"]
    rows = [head, ["", "", "", "", "", initials]]
    for habit in log.habits.values():
        done = log.done[habit.name]
        s = streak(habit, done, today)
        have, need = progress(habit, done, today)
        if isinstance(habit.schedule, OnDays):
            due_today = habit.schedule.period(today) is not None
            now = paint("✓", GREENS[4]) if today in done else "due" if due_today else "-"
        else:
            now = paint(f"{have}/{need}", GREENS[4] if have >= need else None)
        current = s.label(s.current)
        if s.at_risk:
            current = paint(f"{current} !", YELLOW)
        elif s.current and s.current == s.longest:
            current = paint(current, GREENS[4], bold=True)  # a personal best, live right now
        strip = "".join(_day_cell(habit, done, d, today) for d in recent)
        rows.append([habit.name, spec(habit.schedule), now, current, s.label(s.longest), strip])
    widths = [max(width(row[i]) for row in rows) for i in range(len(head))]
    lines = ["  ".join(pad(cell, w) for cell, w in zip(row, widths, strict=True)) for row in rows]
    legend = "● done  · missed  ! keep the streak alive: due today / this week"
    return "\n".join(line.rstrip() for line in [*lines, "", legend])


def month_view(
    habit: Habit, done: set[date], year: int, month: int, today: date, *, sunday: bool = False
) -> str:
    """A `cal`-style month for one habit, built on `calendar.Calendar.monthdatescalendar`."""
    cal = calendar.Calendar(firstweekday=calendar.SUNDAY if sunday else calendar.MONDAY)
    schedule = habit.schedule
    title = f"{calendar.month_name[month]} {year}"
    header = " ".join(f"{DAY_NAMES[d][:2].title():>3}" for d in cal.iterweekdays())
    lines = [f"{title:^{len(header)}}   {habit.name} · {spec(habit.schedule)}", header]
    per_week = counts(habit, done)
    for week in cal.monthdatescalendar(year, month):  # whole weeks, padded with other months
        cells = []
        for d in week:
            if d.month != month:
                cells.append("   ")
                continue
            number = paint(f"{d.day:>2}", under=d == today)
            cells.append(number + _day_cell(habit, done, d, today))
        line = " ".join(cells)
        if isinstance(schedule, PerWeek) and week[0] <= today:
            # PerWeek weeks run Monday to Sunday; with --sunday, count the week the row ends in.
            have = per_week[schedule.period(week[-1])]
            colour = GREENS[4] if have >= schedule.need else RED if week[-1] < today else None
            line += "   " + paint(f"{have}/{schedule.need}", colour)
        lines.append(line.rstrip())
    return "\n".join(lines)


def _level(done_count: int, total: int) -> int:
    """0-4, like GitHub: any check-in at all is at least level 1."""
    if done_count == 0 or total == 0:
        return 0
    return max(1, round(4 * done_count / total))


def heatmap(log: Log, today: date, *, weeks: int = 26, only: Iterable[Habit] | None = None) -> str:
    """Weeks run left to right, Monday to Sunday top to bottom; the colour is how much got done."""
    habits = list(only if only is not None else log.habits.values())
    if not habits:
        return "No habits yet. Start one with: habit add run --every daily"
    start = today - timedelta(days=today.weekday() + 7 * (weeks - 1))  # a Monday
    columns = [[start + timedelta(days=7 * w + d) for d in range(7)] for w in range(weeks)]

    labels = [" "] * (2 * weeks)
    for w, column in enumerate(columns):  # a month's name goes over the week its 1st falls in
        first = next((d for d in column if d.day == 1), column[0] if w == 0 else None)
        if first and all(c == " " for c in labels[2 * w : 2 * w + 4]):
            labels[2 * w : 2 * w + 3] = calendar.month_abbr[first.month]
    lines = ["     " + "".join(labels).rstrip()]

    totals = {d: sum(d in log.done[h.name] for h in habits) for column in columns for d in column}
    for weekday in range(7):
        row = []
        for column in columns:
            d = column[weekday]
            if d > today:
                row.append("  ")
                continue
            level = _level(totals[d], len(habits))
            row.append(paint(LEVEL_GLYPHS[level], GREENS[level]) + " ")
        name = DAY_NAMES[weekday].title() if weekday % 2 == 0 else ""
        lines.append(f"{name:<4} " + "".join(row).rstrip())

    count = sum(totals[d] for d in totals if d <= today)
    scope = habits[0].name if len(habits) == 1 else f"{len(habits)} habits"
    legend = " ".join(paint(g, c) for g, c in zip(LEVEL_GLYPHS, GREENS, strict=True))
    lines += ["", f"{count} check-ins in {weeks} weeks ({scope})    less {legend} more"]
    return "\n".join(lines)
