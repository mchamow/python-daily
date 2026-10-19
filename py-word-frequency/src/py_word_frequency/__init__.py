"""wordfreq: the most frequent, and the most distinctive, words across text files."""

import argparse
import sys
from collections import Counter
from collections.abc import Sequence

from .analysis import count_words, distinctive_words, filter_counts
from .report import as_json, bar_chart, distinctive_chart, summary
from .sources import SourceError, iter_sources
from .text import STOP_WORDS, words


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wordfreq",
        description="Count the most frequent (or most distinctive) words in text files.",
        epilog="Example: wordfreq data/ -n 15 --ignore said",
    )
    parser.add_argument(
        "paths", nargs="+", metavar="PATH", help="files, directories (recursive) or - for stdin"
    )
    parser.add_argument("-n", "--top", type=int, default=10, help="how many words (default: 10)")
    parser.add_argument(
        "--min-length", type=int, default=3, metavar="N", help="ignore shorter words (default: 3)"
    )
    parser.add_argument(
        "--ignore",
        action="append",
        default=[],
        metavar="WORD",
        help="extra stop word; repeat for more",
    )
    parser.add_argument(
        "--keep-stop-words", action="store_true", help="count 'the', 'and', ... as well"
    )
    parser.add_argument(
        "--glob", default="*.txt", help="file pattern inside directories (default: *.txt)"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--distinctive",
        action="store_true",
        help="per file: words most over-represented compared with the other files",
    )
    mode.add_argument("--json", action="store_true", help="machine-readable output")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    stop_words = frozenset() if args.keep_stop_words else STOP_WORDS
    stop_words |= {word.casefold() for word in args.ignore}

    try:
        sources = list(iter_sources(args.paths, pattern=args.glob))
    except SourceError as e:
        print(f"wordfreq: {e}", file=sys.stderr)
        return 2

    raw = {source.name: count_words(words(source.text)) for source in sources}
    per_doc = {
        name: filter_counts(counts, min_length=args.min_length, stop_words=stop_words)
        for name, counts in raw.items()
    }
    scanned = sum(counts.total() for counts in raw.values())
    counted: Counter[str] = sum(per_doc.values(), Counter())

    if args.json:
        print(as_json(per_doc, scanned, counted, args.top))
    elif args.distinctive:
        if len(per_doc) < 2:
            print("wordfreq: --distinctive needs at least two files to compare", file=sys.stderr)
            return 2
        print(distinctive_chart(distinctive_words(per_doc, top=args.top)))
    else:
        print(summary(per_doc, scanned, counted), end="\n\n")
        print(bar_chart(counted.most_common(args.top)))
    return 0
