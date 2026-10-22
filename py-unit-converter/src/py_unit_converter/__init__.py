"""conv: exact unit conversions as a one-shot command, a REPL, or a filter over stdin."""

import argparse
import sys
from collections.abc import Iterable, Sequence
from contextlib import suppress
from typing import TextIO

from .parser import MAX_DIGITS
from .session import Session
from .units import ConversionError

BANNER = "conv: exact unit conversions. Try '10 km to mi', 'help', or Ctrl-D to leave."


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="conv",
        description="Convert units exactly. With no expression, starts a REPL "
        "(or reads one expression per line from piped stdin).",
        epilog="examples: conv 10 km to mi | conv 5 ft 11 in to cm | conv 98.6 F to C",
    )
    parser.add_argument("expression", nargs="*", help="e.g. 10 km to mi")
    parser.add_argument(
        "-d", "--digits", type=int, default=10, choices=range(1, MAX_DIGITS + 1),
        metavar=f"1-{MAX_DIGITS}", help="significant digits to show (default: 10)",
    )  # fmt: skip
    return parser


def run_lines(session: Session, lines: Iterable[str], out: TextIO, err: TextIO) -> int:
    """Batch mode: one expression per line. Bad lines are reported and skipped, not fatal."""
    status = 0
    for number, line in enumerate(lines, start=1):
        try:
            reply = session.execute(line)
        except ConversionError as error:
            print(f"conv: line {number}: {error}", file=err)
            status = 1
            continue
        if reply is None:
            break
        if reply:
            print(reply, file=out)
    return status


def repl(session: Session) -> int:
    # Importing readline gives input() arrow-key editing and history. It's missing on some
    # platforms, and the REPL works without it.
    with suppress(ImportError):
        import readline  # noqa: F401
    print(BANNER)
    while True:
        try:
            line = input("> ")
        except EOFError:  # Ctrl-D
            print()
            return 0
        except KeyboardInterrupt:  # Ctrl-C abandons the line, like a shell
            print()
            continue
        try:
            reply = session.execute(line)
        except ConversionError as error:
            reply = f"error: {error}"
        if reply is None:
            return 0
        if reply:
            print(reply)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    session = Session(digits=args.digits)
    if args.expression:
        return run_lines(session, [" ".join(args.expression)], sys.stdout, sys.stderr)
    if sys.stdin.isatty():
        return repl(session)
    return run_lines(session, sys.stdin, sys.stdout, sys.stderr)
