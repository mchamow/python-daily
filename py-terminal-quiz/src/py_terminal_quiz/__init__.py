"""quiz: a timed terminal quiz from a CSV file, with replayable seeds and a high-score table."""

import argparse
import getpass
import os
import random
import sys
from collections import Counter
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from . import scores
from .game import play, summary
from .questions import Difficulty, Question, RowError, load_questions, pick

DEFAULT_FILE = Path("data/general.csv")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    path: Path = args.scores or default_scores_path()
    try:
        boards = scores.load(path)
    except scores.ScoreFileError as error:
        print(f"quiz: {error}", file=sys.stderr)
        return 1
    if args.top:
        print(scores.render(boards))
        return 0

    questions = _load_or_exit(args.file)
    if args.list:
        print(_categories(questions))
        return 0
    seed: scores.Seed = args.seed if args.seed is not None else random.randrange(10_000)
    if args.daily:
        seed = date.today().isoformat()  # everyone who plays today gets the same quiz
    rng = random.Random(seed)  # our own generator, not the hidden module-wide one
    try:
        chosen = pick(questions, args.count, rng, category=args.category, difficulty=args.level)
    except LookupError as error:
        print(f"quiz: {error}", file=sys.stderr)
        return 1

    print(f"{args.file.stem} · {len(chosen)} questions · {args.time:g}s each · seed {seed}")
    print(f"Replay this exact quiz: quiz {_replay_args(args, seed)}")
    print("Type the answer or its letter. Blank skips, :q quits.")
    try:
        answers = play(chosen, rng, limit=args.time, ask=_ask)
    except KeyboardInterrupt:
        print("\nQuiz abandoned; no score saved.")
        return 130  # 128 + SIGINT, the shell convention

    print("\n" + summary(answers))
    if not any(a.points for a in answers):
        return 0  # a game without a single point isn't worth a place on the board
    entry = scores.Entry(
        name=args.name,
        score=sum(a.points for a in answers),
        correct=sum(a.verdict.scores for a in answers),  # bools sum as 0/1
        total=len(answers),
        seconds=round(sum(a.seconds for a in answers), 2),
        seed=seed,
        played=date.today().isoformat(),
    )
    key = _board_key(args, len(chosen))
    rank = scores.record(boards, key, entry)
    scores.save(path, boards)
    match rank:
        case 1:
            print(f"\n🎉 New high score for {key}!")
        case int():
            print(f"\nYou placed #{rank} on {key}.")
        case None:
            print(f"\nNot in the top {scores.KEEP} for {key} this time.")
    print(scores.render(boards, key, highlight=entry))
    return 0


def default_scores_path() -> Path:
    return Path(os.environ.get("QUIZ_SCORES", Path.home() / ".quiz-scores.json"))


def _load_or_exit(path: Path) -> list[Question]:
    # One try can't mix `except` and `except*`, hence two. A plain OSError raised inside
    # passes through `except*` unwrapped and reaches the outer handler as itself.
    try:
        try:
            return load_questions(path)
        except* RowError as group:
            # `return` is a SyntaxError inside except*; raising (sys.exit raises) is allowed.
            for problem in group.exceptions:
                print(f"quiz: {path}, {problem}", file=sys.stderr)
            sys.exit(f"quiz: {group.message}; fix the file and try again")
    except OSError as error:
        sys.exit(f"quiz: can't read {path}: {error.strerror}")


def _ask(prompt: str) -> str:
    reply = input(prompt)
    if not sys.stdin.isatty():
        print(reply)  # a terminal echoes what you type; piped input doesn't, so echo it here
    return reply


def _board_key(args: argparse.Namespace, count: int) -> str:
    parts = [args.file.stem, f"{count}q", args.category, args.level]
    return " · ".join(str(p) for p in parts if p)


def _replay_args(args: argparse.Namespace, seed: scores.Seed) -> str:
    flags = [] if args.file == DEFAULT_FILE else [str(args.file)]
    flags += ["--seed", str(seed), "-n", str(args.count)]
    if args.category:
        flags += ["-c", args.category]
    if args.level:
        flags += ["-d", str(args.level)]
    return " ".join(flags)


def _categories(questions: list[Question]) -> str:
    counts = Counter((q.category, q.difficulty) for q in questions)
    lines = [f"{'category':<12}" + "".join(f"{d:>8}" for d in Difficulty)]
    for category in sorted({q.category for q in questions}):
        lines.append(f"{category:<12}" + "".join(f"{counts[category, d]:>8}" for d in Difficulty))
    return "\n".join(lines) + f"\n{len(questions)} questions"


def _seed(text: str) -> scores.Seed:
    # random.Random takes str seeds too, but "42" and 42 are different seeds, so normalise.
    return int(text) if text.lstrip("-").isdigit() else text


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="quiz", description=__doc__)
    p.add_argument("file", nargs="?", type=Path, default=DEFAULT_FILE, help="questions CSV")
    p.add_argument("-n", "--count", type=int, default=5, help="questions per game (default 5)")
    p.add_argument("-c", "--category", help="only this category")
    p.add_argument("-d", "--difficulty", dest="level", type=Difficulty, choices=list(Difficulty))
    p.add_argument("-t", "--time", type=float, default=20, help="seconds per question")
    seeding = p.add_mutually_exclusive_group()
    seeding.add_argument("--seed", type=_seed, help="replay a quiz: same seed, same questions")
    seeding.add_argument("--daily", action="store_true", help="today's quiz, the same for all")
    p.add_argument("--name", default=getpass.getuser(), help="name on the high-score table")
    p.add_argument("--scores", type=Path, help="score file (default $QUIZ_SCORES or ~)")
    p.add_argument("--list", action="store_true", help="show the categories and stop")
    p.add_argument("--top", action="store_true", help="show the high-score tables and stop")
    return p
