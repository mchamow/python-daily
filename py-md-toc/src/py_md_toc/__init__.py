"""mdtoc: keep a GitHub-compatible table of contents in your Markdown files.

mdtoc README.md docs/          # write or refresh the TOC in place
mdtoc --check .                # CI mode: exit 1 if a TOC is stale or an #anchor is broken
mdtoc --diff README.md         # show what would change, touch nothing
cat notes.md | mdtoc -         # filter stdin to stdout
"""

import argparse
import difflib
import re
import sys
from pathlib import Path

from .files import markdown_files, read_text, write_text
from .toc import TocError, Update, update

LEVELS = re.compile(r"(?P<low>[1-6])(?:-(?P<high>[1-6]))?")


def parse_levels(spec: str) -> range:
    """`2-3` → range(2, 4); `2` → range(2, 3). Used as an argparse `type=`."""
    m = LEVELS.fullmatch(spec)
    if not m:
        raise argparse.ArgumentTypeError(f"{spec!r} isn't a level range like 2-3")
    low, high = int(m["low"]), int(m["high"] or m["low"])
    if high < low:
        raise argparse.ArgumentTypeError(f"{spec!r} runs backwards")
    return range(low, high + 1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mdtoc",
        description="Insert or refresh a table of contents between <!-- toc --> and "
        "<!-- /toc --> markers. Without markers, the TOC goes above the first listed heading.",
    )
    parser.add_argument(
        "paths", nargs="+", type=Path, help="Markdown files or directories; - for stdin"
    )
    parser.add_argument(
        "-l",
        "--levels",
        type=parse_levels,
        default=range(2, 4),
        metavar="N-M",
        help="heading levels to list (default: 2-3)",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check", action="store_true", help="change nothing; exit 1 if anything is off"
    )
    mode.add_argument("--diff", action="store_true", help="print a unified diff; change nothing")
    return parser


def report_links(name: str, result: Update) -> None:
    for link in result.broken:
        hint = f" (did you mean #{link.suggestion}?)" if link.suggestion else ""
        print(f"{name}:{link.line}: broken link #{link.anchor}{hint}", file=sys.stderr)


def show_diff(name: str, result: Update) -> None:
    sys.stdout.writelines(
        difflib.unified_diff(
            result.before.splitlines(keepends=True),
            result.after.splitlines(keepends=True),
            fromfile=f"a/{name}",
            tofile=f"b/{name}",
        )
    )


def main(argv: list[str] | None = None) -> int:
    """Entry point. The console script passes the return value to sys.exit()."""
    args = build_parser().parse_args(argv)

    if args.paths == [Path("-")]:
        try:
            result = update(sys.stdin.read(), args.levels)
        except TocError as e:
            print(f"mdtoc: <stdin>:{e.line}: {e}", file=sys.stderr)
            return 2
        sys.stdout.write(result.after)
        report_links("<stdin>", result)
        return 0

    status = 0
    for path in markdown_files(args.paths):
        name = path.as_posix()
        try:
            result = update(read_text(path), args.levels)
        except (OSError, UnicodeDecodeError) as e:
            print(f"mdtoc: {name}: {e}", file=sys.stderr)
            status = 2
            continue
        except TocError as e:
            print(f"mdtoc: {name}:{e.line}: {e}", file=sys.stderr)
            status = 2
            continue

        report_links(name, result)
        if args.diff:
            show_diff(name, result)
        elif args.check:
            problems = ["TOC out of date"] if result.changed else []
            if n := len(result.broken):
                problems.append(f"{n} broken link{'s' if n > 1 else ''}")
            detail = f" ({', '.join(problems)})" if problems else ""
            print(f"{'FAIL' if problems else 'ok':<8}{name}{detail}")
        elif result.changed:
            write_text(path, result.after)
            print(f"{'updated':<8}{name} ({result.entries} entries)")
        else:
            print(f"{'ok':<8}{name}")

        if args.check and (result.changed or result.broken):
            status = max(status, 1)
    return status
