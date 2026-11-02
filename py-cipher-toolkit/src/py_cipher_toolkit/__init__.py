"""`cipher`: encrypt, decrypt and crack classical ciphers from the command line.

    cipher caesar -s 3 "Attack at dawn"          cipher vigenere -k LEMON -f message.txt
    cipher atbash "Wrnvmhrlm"                     cipher freq -f data/secret.txt
    cipher crack -f data/secret.txt --explain     echo "..." | cipher crack

Text comes from the TEXT argument, from `-f FILE`, or from stdin, in that order.
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from .analysis import letters_only
from .ciphers import atbash, caesar, vigenere
from .crack import crack
from .report import render_frequencies, render_key_lengths

SHORT = 100  # below this many letters, frequency analysis is a coin toss and we say so


def _parser() -> argparse.ArgumentParser:
    source = argparse.ArgumentParser(add_help=False)
    source.add_argument("text", nargs="?", help="the text (default: -f FILE, else stdin)")
    source.add_argument("-f", "--file", type=Path, help="read the text from a file")

    direction = argparse.ArgumentParser(add_help=False)
    direction.add_argument("-d", "--decrypt", action="store_true", help="decrypt instead")

    parser = argparse.ArgumentParser(prog="cipher", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("caesar", parents=[source, direction], help="shift every letter")
    p.add_argument("-s", "--shift", type=int, required=True, help="places to shift (any int)")
    p = sub.add_parser("vigenere", parents=[source, direction], help="shift by a keyword")
    p.add_argument("-k", "--key", required=True, help="the keyword, ASCII letters only")
    sub.add_parser("atbash", parents=[source], help="mirror the alphabet (its own inverse)")
    sub.add_parser("freq", parents=[source], help="letter frequencies vs. English")
    p = sub.add_parser("crack", parents=[source], help="find the key by frequency analysis")
    p.add_argument("--max-key", type=int, default=20, metavar="N", help="longest key to try")
    p.add_argument("--explain", action="store_true", help="show how the key was found")
    return parser


def _read(args: argparse.Namespace, parser: argparse.ArgumentParser) -> str:
    if args.text is not None:
        return str(args.text)
    if args.file is not None:
        try:
            return Path(args.file).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            parser.exit(1, f"cipher: can't read {args.file}: {e}\n")
    if sys.stdin.isatty():
        parser.error("give the text as an argument, with -f FILE, or on stdin")
    return sys.stdin.read()


def _print_crack(text: str, max_key: int, explain: bool) -> None:
    report = crack(text, max_key_length=max_key)
    best = report.best
    count = len(letters_only(text))
    if count < SHORT:
        print(f"Only {count} letters: the guesses below are shaky.\n", file=sys.stderr)
    if explain:
        print(render_key_lengths(report), end="\n\n")
    print(f"Best guess: {best.describe()}  (χ² {best.score:,.1f})")
    print(best.plaintext.rstrip("\n"), end="\n\n")
    print("Runners-up (χ²: lower is more English):")
    for other in report.candidates[1:4]:
        preview = " ".join(other.plaintext.split())[:48]
        print(f"  {other.score:>9,.1f}  {other.describe():<40} {preview}…")


def main(argv: Sequence[str] | None = None) -> None:
    parser = _parser()
    args = parser.parse_args(argv)
    text = _read(args, parser)

    try:
        match args.command:
            case "caesar":
                out = caesar(text, -args.shift if args.decrypt else args.shift)
            case "vigenere":
                out = vigenere(text, args.key, decrypt=args.decrypt)
            case "atbash":
                out = atbash(text)
            case "freq":
                out = render_frequencies(text)
            case "crack":
                return _print_crack(text, args.max_key, args.explain)
            case other:
                parser.error(f"unknown command {other!r}")
    except ValueError as e:
        parser.error(str(e))
    print(out, end="" if out.endswith("\n") else "\n")
