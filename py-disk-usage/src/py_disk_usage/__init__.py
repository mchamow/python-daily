"""dux: where did my disk go? A du-style tree with bars, or the largest files under a path."""

import argparse
import os
import sys
import time
from pathlib import Path

from .render import Unit, render
from .scan import Options, Problem, scan
from .walk import largest

MAX_PROBLEMS_SHOWN = 5


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="dux", description="Show what takes up space under PATH, biggest first."
    )
    parser.add_argument("path", nargs="?", type=Path, default=Path("."))
    parser.add_argument("-d", "--depth", type=int, default=2, help="levels to show (default 2)")
    parser.add_argument("-n", "--limit", type=int, default=8, help="entries per dir (default 8)")
    parser.add_argument("-l", "--largest", type=int, metavar="N", help="the N largest files")
    parser.add_argument(
        "-e",
        "--exclude",
        action="append",
        default=[],
        metavar="GLOB",
        help="skip names matching GLOB (repeatable): -e .git -e '*.pyc'",
    )
    parser.add_argument("-A", "--apparent", action="store_true", help="file lengths, not blocks")
    parser.add_argument("-x", "--one-file-system", action="store_true", help="don't cross mounts")
    parser.add_argument("--si", action="store_true", help="powers of 1000 (kB, MB), not 1024")
    args = parser.parse_args(argv)
    if args.depth < 0 or args.limit < 1 or (args.largest is not None and args.largest < 1):
        parser.error("--depth must be >= 0; --limit and --largest >= 1")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    options = Options(args.apparent, args.one_file_system, tuple(args.exclude))
    unit: Unit = "H" if args.si else "h"
    measure = "apparent size" if args.apparent else "on disk"
    problems: list[Problem] = []

    started = time.perf_counter()
    try:
        if args.largest is not None:
            files = largest(args.path, args.largest, options, problems.append)
            for f in files:
                print(f"{f.size:>10.1{unit}}  {os.path.relpath(f.path, args.path)}")
            footer = f"{len(files)} largest files, {measure}"
        else:
            result = scan(args.path, options)
            problems.extend(result.problems)
            for line in render(result.root, depth=args.depth, limit=args.limit, unit=unit):
                print(line)
            footer = f"{result.root.size:,} bytes {measure}"
        print(f"\n{footer} · scanned in {time.perf_counter() - started:.2f}s")
    except FileNotFoundError:
        print(f"dux: {args.path}: no such file or directory", file=sys.stderr)
        return 2
    except RecursionError:
        print(f"dux: {args.path}: directories nested too deeply to recurse", file=sys.stderr)
        return 2
    except BrokenPipeError:
        # `dux | head` closed the pipe early. That's fine, so stop Python reporting the failed
        # flush at exit by pointing stdout at /dev/null.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return 0

    for p in problems[:MAX_PROBLEMS_SHOWN]:
        print(f"dux: {p.path}: {p.message}", file=sys.stderr)
    if len(problems) > MAX_PROBLEMS_SHOWN:
        print(f"dux: ... and {len(problems) - MAX_PROBLEMS_SHOWN} more", file=sys.stderr)
    return 1 if problems else 0  # like du: print the partial answer, but exit 1
