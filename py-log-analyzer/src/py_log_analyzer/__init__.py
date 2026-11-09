"""logscan: stream access logs (plain, gzip, bzip2, xz, zstd or stdin) through a lazy pipeline and
report traffic, errors, incidents, slow endpoints and top clients in constant memory.
"""

import argparse
import os
import sys
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from py_log_analyzer.parse import Intake, Request, parse
from py_log_analyzer.report import render
from py_log_analyzer.source import read_lines
from py_log_analyzer.stats import analyze


def _when(text: str) -> datetime:
    """An ISO time for --since/--until. Naive times are taken as UTC: comparing a naive datetime
    with the log's aware ones would raise TypeError on the first line."""
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not an ISO date/time: {text!r}") from None
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="logscan",
        description="Stream access logs and report errors, slow endpoints and top clients.",
    )
    p.add_argument("files", nargs="+", help="log files, compressed or not; '-' reads stdin")
    p.add_argument("-n", "--top", type=int, default=5, metavar="N", help="rows per table")
    p.add_argument(
        "--since", type=_when, help="skip requests before this, e.g. 2026-11-08T14:00+01:00"
    )
    p.add_argument("--until", type=_when, help="skip requests at or after this")
    return p


def pipeline(
    files: list[str], intake: Intake, since: datetime | None, until: datetime | None
) -> Iterator[Request]:
    """Wire the stages together. Nothing runs here: each stage is a lazy generator."""
    requests = parse(read_lines(files), intake)
    if since is not None:
        requests = (r for r in requests if r.time >= since)
    if until is not None:
        requests = (r for r in requests if r.time < until)
    return requests


def peak_rss() -> int | None:
    """Peak resident memory in bytes, or None where the `resource` module doesn't exist."""
    try:
        import resource
    except ImportError:  # Windows
        return None
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak if sys.platform == "darwin" else peak * 1024  # bytes on macOS, KiB on Linux


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if missing := [f for f in args.files if f != "-" and not Path(f).is_file()]:
        print(f"logscan: no such file: {', '.join(missing)}", file=sys.stderr)
        return 2

    intake = Intake()
    started = time.perf_counter()
    try:
        stats = analyze(pipeline(args.files, intake, args.since, args.until), top=args.top)
    except KeyboardInterrupt:
        return 130
    except EOFError as error:  # a truncated .gz/.zst: raised mid-stream, after real lines
        print(f"logscan: a compressed file ends early ({error})", file=sys.stderr)
        return 1
    except OSError as error:  # unreadable file, corrupt archive
        print(f"logscan: {error}", file=sys.stderr)
        return 1
    elapsed = time.perf_counter() - started

    try:
        for line in render(stats, intake):
            print(line)
        sys.stdout.flush()
    except BrokenPipeError:
        # `logscan … | head` closed the pipe. Point stdout at devnull so Python's own flush at
        # exit doesn't raise a second time (the recipe from the `signal` module docs).
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return 0

    rss = peak_rss()
    memory = f" · peak memory {rss / 2**20:.0f} MiB" if rss else ""
    print(
        f"\n{intake.lines:,} lines in {elapsed:.2f} s "
        f"({intake.lines / elapsed / 1000:,.0f}k lines/s){memory}",
        file=sys.stderr,
    )
    return 0
