"""The habit log: a plain-text file you can read, grep, diff and fix by hand.

    # habit NAME SCHEDULE SINCE
    habit run   daily     2026-06-01
    habit gym   3/week    2026-06-01
    2026-06-01 run
    2026-06-02 run
    2026-06-02 gym

`done` appends one line, so the file is also an audit trail. Only `undo` rewrites it.
"""

import os
import re
import tempfile
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from .schedule import Schedule, day_number, parse_schedule, spec

NAME = re.compile(r"[a-z][\w-]*", re.IGNORECASE)


class LogError(Exception):
    """A line of the log file that can't be read; the message names the line."""


@dataclass(frozen=True, slots=True)
class Habit:
    name: str
    schedule: Schedule
    since: date


@dataclass(slots=True)
class Log:
    path: Path
    habits: dict[str, Habit] = field(default_factory=dict)  # in the order they were added
    done: defaultdict[str, set[date]] = field(default_factory=lambda: defaultdict(set))

    def habit(self, name: str) -> Habit:
        try:
            return self.habits[name.lower()]
        except KeyError:
            known = ", ".join(self.habits) or "none yet; add one with `habit add NAME`"
            raise LookupError(f"no habit called {name!r} (habits: {known})") from None


def load(path: Path) -> Log:
    """Read the log. A missing file is an empty log, not an error."""
    log = Log(path)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return log
    for number, raw in enumerate(text.splitlines(), start=1):
        try:
            _read_line(log, raw.partition("#")[0])
        except ValueError as e:
            raise LogError(f"{path}:{number}: {e}\n    {raw.strip()}") from None
    return log


def _read_line(log: Log, line: str) -> None:
    match line.split():
        case []:
            pass
        case ["habit", name, schedule, since] if NAME.fullmatch(name):
            log.habits[name.lower()] = Habit(
                name.lower(), parse_schedule(schedule), date.fromisoformat(since)
            )
        case ["habit", *_]:
            raise ValueError(
                "expected `habit NAME SCHEDULE SINCE`, e.g. `habit run daily 2026-06-01`"
            )
        case [day, name] if name.lower() in log.habits:
            log.done[name.lower()].add(date.fromisoformat(day))
        case [_, name]:
            raise ValueError(f"check-in for {name!r} before a `habit {name} …` line declares it")
        case _:
            raise ValueError("expected `habit NAME SCHEDULE SINCE` or `YYYY-MM-DD NAME`")


def add_habit(log: Log, name: str, schedule: Schedule, since: date) -> Habit:
    if not NAME.fullmatch(name):
        raise ValueError(f"a habit name is a letter, then letters, digits, _ or -, not {name!r}")
    if name.lower() in log.habits:
        raise ValueError(f"there is already a habit called {name.lower()!r}")
    habit = Habit(name.lower(), schedule, since)
    _append(log.path, f"habit {habit.name} {spec(schedule)} {since}")
    log.habits[habit.name] = habit
    return habit


def check_in(log: Log, habit: Habit, day: date) -> bool:
    """Record `day`. Returns False (and writes nothing) if it was already recorded."""
    if day in log.done[habit.name]:
        return False
    _append(log.path, f"{day} {habit.name}")  # str(date) is ISO 8601: 2026-11-03
    log.done[habit.name].add(day)
    return True


def undo(log: Log, habit: Habit, day: date) -> bool:
    """Remove the check-in for `day`. Returns False if there wasn't one."""
    if day not in log.done[habit.name]:
        return False
    target = [str(day), habit.name]
    lines = log.path.read_text(encoding="utf-8").splitlines(keepends=True)
    kept = [line for line in lines if line.partition("#")[0].lower().split() != target]
    _replace(log.path, "".join(kept))
    log.done[habit.name].discard(day)
    return True


def parse_day(text: str, today: date) -> date:
    """`today`, `yesterday`, `-3` (days ago), a weekday (the most recent one) or YYYY-MM-DD."""
    word = text.strip().lower()
    match word:
        case "today":
            day = today
        case "yesterday":
            day = today - timedelta(days=1)
        case _ if re.fullmatch(r"-\d+", word):
            day = today + timedelta(days=int(word))
        case _ if (weekday := _weekday(word)) is not None:
            day = today - timedelta(days=(today.weekday() - weekday) % 7)
        case _:
            try:
                day = date.fromisoformat(word)
            except ValueError:
                raise ValueError(
                    f"can't read day {text!r}: use today, yesterday, -3, a weekday or YYYY-MM-DD"
                ) from None
    if day > today:
        raise ValueError(f"{day} is in the future: habits are recorded after the fact")
    return day


def _weekday(word: str) -> int | None:
    try:
        return day_number(word)
    except ValueError:
        return None


def _append(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    needs_newline = path.exists() and path.stat().st_size > 0 and not _ends_with_newline(path)
    with path.open("a", encoding="utf-8") as f:  # "a" is O_APPEND: writes land at the end
        f.write(("\n" if needs_newline else "") + line + "\n")


def _ends_with_newline(path: Path) -> bool:
    with path.open("rb") as f:
        f.seek(-1, os.SEEK_END)
        return f.read(1) == b"\n"


def _replace(path: Path, text: str) -> None:
    """Atomic rewrite (the Day 4 recipe): write a temp file next to it, then rename over it."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
