"""`habit`: track habits, keep streaks, and see them as a calendar or a heatmap.

habit add run --every daily        habit add gym --every 3/week
habit done run                     habit done gym yesterday
habit                              (the status table)
habit cal run                      habit year
"""

import argparse
import os
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from .log import Log, LogError, add_habit, check_in, load, parse_day, undo
from .render import heatmap, month_view, plain, status_table, wants_colour
from .schedule import parse_schedule, spec
from .streaks import streak


def _default_file() -> Path:
    return Path(os.environ.get("HABITS_FILE") or Path.home() / ".habits.log")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="habit", description=__doc__.splitlines()[0])
    parser.add_argument(
        "-f",
        "--file",
        type=Path,
        default=None,
        help="the log file (default: $HABITS_FILE, else ~/.habits.log)",
    )
    parser.add_argument("--color", choices=["auto", "always", "never"], default="auto")
    parser.add_argument(
        "--today",
        type=date.fromisoformat,
        default=None,
        metavar="YYYY-MM-DD",
        help="pretend today is this date (for demos and back-filling)",
    )
    sub = parser.add_subparsers(dest="command")  # no command means `status`

    sub.add_parser("status", help="every habit's streak and its last 14 days (the default)")
    p = sub.add_parser("add", help="start tracking a habit")
    p.add_argument("name")
    p.add_argument(
        "-e",
        "--every",
        default="daily",
        help="daily, weekdays, weekends, mon,wed,fri or 3/week (default: daily)",
    )
    p.add_argument("--since", default="today", help="when it starts counting (default: today)")
    for name, verb in (("done", "record"), ("undo", "remove")):
        p = sub.add_parser(name, help=f"{verb} a check-in")
        p.add_argument("name")
        p.add_argument(
            "days",
            nargs="*",
            default=["today"],
            help="today (default), yesterday, -2, a weekday like mon, or YYYY-MM-DD",
        )
    p = sub.add_parser("cal", help="a month calendar for one habit")
    p.add_argument("name")
    p.add_argument("month", nargs="?", help="YYYY-MM (default: this month)")
    p.add_argument("--sunday", action="store_true", help="start weeks on Sunday")
    p = sub.add_parser("year", help="a GitHub-style heatmap of check-ins")
    p.add_argument("name", nargs="?", help="just this habit (default: all of them)")
    p.add_argument("-w", "--weeks", type=int, default=26, help="how many weeks (default: 26)")
    return parser


def _run(args: argparse.Namespace, log: Log, today: date) -> str:
    match args.command:
        case None | "status":
            return status_table(log, today)
        case "add":
            habit = add_habit(
                log, args.name, parse_schedule(args.every), parse_day(args.since, today)
            )
            return (
                f"Tracking {habit.name} ({spec(habit.schedule)}) since {habit.since:%a %d %b %Y}."
            )
        case "done" | "undo":
            habit = log.habit(args.name)
            act = check_in if args.command == "done" else undo
            lines = []
            for day in sorted({parse_day(text, today) for text in args.days}):
                changed = act(log, habit, day)
                what = "recorded" if args.command == "done" else "removed"
                lines.append(f"{habit.name} {day:%a %d %b}: {what if changed else 'no change'}")
            s = streak(habit, log.done[habit.name], today)
            lines.append(f"Streak: {s.label(s.current)} (best {s.label(s.longest)})")
            return "\n".join(lines)
        case "cal":
            habit = log.habit(args.name)
            first = date.fromisoformat(f"{args.month}-01") if args.month else today.replace(day=1)
            return month_view(habit, log.done[habit.name], first.year, first.month, today,
                              sunday=args.sunday)  # fmt: skip
        case "year":
            only = [log.habit(args.name)] if args.name else None
            return heatmap(log, today, weeks=max(1, args.weeks), only=only)
        case other:
            raise AssertionError(f"unhandled command {other!r}")


def main(argv: Sequence[str] | None = None) -> None:
    parser = _parser()
    args = parser.parse_args(argv)
    path = args.file or _default_file()
    today = args.today or date.today()  # local time, not UTC: a habit day is *your* day
    try:
        out = _run(args, load(path), today)
    except LogError as e:
        parser.exit(1, f"habit: {e}\n")
    except (LookupError, ValueError) as e:
        parser.error(str(e))
    except OSError as e:
        parser.exit(1, f"habit: {e}\n")
    print(out if wants_colour(args.color, sys.stdout) else plain(out))
