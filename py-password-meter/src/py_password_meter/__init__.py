"""pw: generate passwords and passphrases, and measure how strong a password really is."""

import argparse
import sys
from collections.abc import Iterable, Sequence
from getpass import getpass
from pathlib import Path

from .generate import CLASSES, Secret, passphrase, password
from .strength import SCENARIOS, Estimate, estimate, human_duration

_FAST_HASH = "offline, fast hash (10B/s)"


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        match args.command:
            case "gen":
                classes = tuple(name for name in CLASSES if name not in args.without)
                secrets = [
                    password(args.length, classes, unambiguous=args.unambiguous)
                    for _ in range(args.count)
                ]
                _print_secrets(secrets)
            case "phrase":
                secrets = [
                    passphrase(
                        args.words,
                        separator=args.sep,
                        capitalize=args.capitalize,
                        number=args.number,
                    )
                    for _ in range(args.count)
                ]
                _print_secrets(secrets)
            case "check":
                _check(args.passwords, args.file)
    except (ValueError, OSError) as error:
        print(f"pw: {error}", file=sys.stderr)
        return 2
    except EOFError:  # Ctrl-D at the hidden prompt
        return 1
    except KeyboardInterrupt:
        return 130
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pw", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    gen = commands.add_parser("gen", help="a random password")
    gen.add_argument("-n", "--length", type=_positive, default=20)
    gen.add_argument("-c", "--count", type=_positive, default=1)
    for name in CLASSES:
        gen.add_argument(
            f"--no-{name}", dest="without", action="append_const", const=name, default=[]
        )
    gen.add_argument("--unambiguous", action="store_true", help="skip look-alikes like l 1 O 0")

    phrase = commands.add_parser("phrase", help="a random passphrase from the EFF wordlist")
    phrase.add_argument("-w", "--words", type=_positive, default=6)
    phrase.add_argument("-c", "--count", type=_positive, default=1)
    phrase.add_argument("-s", "--sep", default="-", help="word separator (default: -)")
    phrase.add_argument("--capitalize", action="store_true")
    phrase.add_argument("--number", action="store_true", help="append a digit to one word")

    check = commands.add_parser("check", help="estimate how hard passwords are to crack")
    check.add_argument("passwords", nargs="*", help="omit to type one hidden, or pipe them in")
    check.add_argument("-f", "--file", type=Path, help="one password per line")
    return parser


def _positive(text: str) -> int:
    if not text.isdecimal() or int(text) < 1:
        raise argparse.ArgumentTypeError(f"expected a whole number of at least 1, got {text!r}")
    return int(text)


def _print_secrets(secrets: list[Secret]) -> None:
    # Secrets go to stdout and commentary to stderr, so 'pw gen | pbcopy' copies only the password.
    for secret in secrets:
        print(secret.text)
    print(f"# {secrets[0].bits:.1f} bits of entropy: {secrets[0].recipe}", file=sys.stderr)


def _check(passwords: list[str], file: Path | None) -> None:
    if file:
        passwords = [*passwords, *file.read_text(encoding="utf-8").splitlines()]
    if passwords:
        candidates, reveal = passwords, True
    elif sys.stdin.isatty():
        candidates, reveal = [getpass("Password (hidden): ")], False
    else:
        candidates, reveal = [line.rstrip("\n") for line in sys.stdin], True

    estimates = [estimate(p) for p in candidates if p]
    if not estimates:
        raise ValueError("nothing to check")
    if len(estimates) == 1:
        print(render_report(estimates[0], reveal=reveal))
    else:
        print(render_table(estimates))


def render_report(est: Estimate, *, reveal: bool = True) -> str:
    """The full breakdown for one password. With reveal=False, no part of it is printed."""
    bar = "█" * (est.score + 1) + "░" * (4 - est.score)
    lines = [
        est.password if reveal else "•" * len(est.password),
        f"  rating     {bar}  {est.rating}",
        f"  naive      {est.naive_bits:5.1f} bits   {len(est.password)} chars, pool of {est.pool}",
        f"  estimated  {est.bits:5.1f} bits   {est.guesses:,} guesses",
        "",
        "  how a cracker sees it",
    ]
    width = max(len(seg.token) for seg in est.segments)
    for seg in est.segments:
        shown = f"{seg.token:<{width}}  {seg.pattern:<10}" if reveal else f"{seg.pattern:<10}"
        detail = seg.detail if reveal else ""
        lines.append(f"    {shown} {seg.guesses:>16,}  {detail}".rstrip())

    lines += ["", "  time to crack"]
    width = max(map(len, SCENARIOS))
    for scenario, seconds in est.crack_times().items():
        lines.append(f"    {scenario:<{width}}  {human_duration(seconds)}")
    if tips := est.tips():
        lines += ["", *(f"  tip: {tip}" for tip in tips)]
    return "\n".join(lines)


def render_table(estimates: Iterable[Estimate]) -> str:
    rows = list(estimates)
    width = max(len("password"), *(len(e.password) for e in rows))
    lines = [f"{'password':<{width}}  naive  estimate  rating       fast-hash crack"]
    for e in rows:
        crack = human_duration(e.crack_times()[_FAST_HASH])
        lines.append(
            f"{e.password:<{width}}  {e.naive_bits:5.1f}  {e.bits:8.1f}  {e.rating:<11}  {crack}"
        )
    return "\n".join(lines)
