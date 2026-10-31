"""Load quiz questions from a CSV file, and pick a (reproducible) random set of them.

One question per row::

    category,difficulty,question,answer,choices
    Geography,easy,What is the capital of Australia?,Canberra,Sydney|Melbourne|Perth
    Geography,medium,What is the capital of Iceland?,Reykjavík|Reykjavik,

``answer`` lists every accepted answer, separated by ``|``; the first one is shown to the player.
``choices`` holds the wrong options of a multiple-choice question; leave it empty for free text.
The delimiter is sniffed, so a semicolon-separated export from Excel loads just the same.
"""

import csv
import random
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from .answers import normalize

COLUMNS = ("category", "difficulty", "question", "answer", "choices")
EXTRA = "__extra__"  # DictReader puts the fields beyond the header here (restkey=)
MAX_WRONG = 5


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

    @property
    def rank(self) -> int:
        # A StrEnum compares as its string value, so sorted() would put "hard" before "medium".
        # Definition order is the real order.
        return list(Difficulty).index(self)


@dataclass(frozen=True, slots=True)
class Question:
    category: str
    difficulty: Difficulty
    text: str
    answers: tuple[str, ...]  # every accepted answer; answers[0] is the one we show
    wrong: tuple[str, ...] = ()  # distractors: non-empty means multiple choice

    @property
    def answer(self) -> str:
        return self.answers[0]


class RowError(ValueError):
    """One bad record. load_questions() raises all of them together, as an ExceptionGroup."""

    def __init__(self, first: int, last: int, message: str) -> None:
        where = f"line {first}" if first == last else f"lines {first}-{last}"
        super().__init__(f"{where}: {message}")


def load_questions(path: Path) -> list[Question]:
    # newline="" hands line endings to the csv module, which needs to see them to handle
    # newlines inside quoted fields. utf-8-sig drops the BOM that Excel puts in front.
    with path.open(newline="", encoding="utf-8-sig") as file:
        dialect = _sniff(file.read(8192))
        file.seek(0)
        reader = csv.DictReader(file, dialect=dialect, restkey=EXTRA)
        missing = [c for c in COLUMNS[:4] if c not in (reader.fieldnames or [])]
        if missing:
            raise ExceptionGroup(
                f"{path} has the wrong header", [RowError(1, 1, f"missing column(s) {missing}")]
            )
        questions: list[Question] = []
        errors: list[RowError] = []
        last = reader.line_num  # line_num counts physical lines, not records
        for row in reader:
            first, last = last + 1, reader.line_num
            try:
                questions.append(_parse(row))
            except ValueError as error:
                errors.append(RowError(first, last, str(error)))
    if errors:
        # Report every bad row at once instead of making the author fix them one run at a time.
        raise ExceptionGroup(f"{len(errors)} bad row(s) in {path}", errors)
    if not questions:
        raise ExceptionGroup(f"{path} is empty", [RowError(1, 1, "no questions after the header")])
    return questions


def _sniff(sample: str) -> type[csv.Dialect] | csv.Dialect:
    try:
        # Restrict the candidates: left alone, the Sniffer weighs every character, and "|"
        # recurs in our cells too.
        return csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:  # "Could not determine delimiter", e.g. a one-column file
        return csv.excel


def _parse(row: dict[str | None, str | list[str] | None]) -> Question:
    if extra := row.get(EXTRA):
        raise ValueError(f"{len(extra)} field(s) more than the header (an unquoted delimiter?)")

    def field(name: str) -> str:
        value = row.get(name)
        return value.strip() if isinstance(value, str) else ""  # None: the row was too short

    text, category = field("question"), field("category")
    if not text or not category:
        raise ValueError("question and category must not be empty")
    try:
        difficulty = Difficulty(field("difficulty").lower())
    except ValueError:
        options = ", ".join(Difficulty)
        raise ValueError(f"difficulty {field('difficulty')!r} is not one of {options}") from None
    answers = _split(field("answer"))
    if not answers:
        raise ValueError("no answer")
    wrong = _split(field("choices"))
    if clash := {normalize(a) for a in answers} & {normalize(w) for w in wrong}:
        raise ValueError(f"{', '.join(sorted(clash))!r} is both right and wrong")
    if len(wrong) > MAX_WRONG:
        raise ValueError(f"at most {MAX_WRONG} wrong choices, got {len(wrong)}")
    return Question(category, difficulty, text, answers, wrong)


def _split(cell: str) -> tuple[str, ...]:
    return tuple(part for p in cell.split("|") if (part := p.strip()))


def pick(
    questions: list[Question],
    count: int,
    rng: random.Random,
    *,
    category: str | None = None,
    difficulty: Difficulty | None = None,
) -> list[Question]:
    """``count`` random questions, easiest first. The same seed always gives the same quiz."""
    pool = [
        q
        for q in questions
        if (category is None or q.category.casefold() == category.casefold())
        and (difficulty is None or q.difficulty is difficulty)
    ]
    if not pool:
        known = ", ".join(sorted({q.category for q in questions}))
        raise LookupError(f"no questions match; categories are: {known}")
    chosen = rng.sample(pool, k=min(count, len(pool)))
    # sorted() is stable, so questions of equal difficulty keep their random order.
    return sorted(chosen, key=lambda q: q.difficulty.rank)


def shuffled_options(question: Question, rng: random.Random) -> list[str]:
    """The multiple-choice options in random order (empty for a free-text question)."""
    if not question.wrong:
        return []
    options = [question.answer, *question.wrong]
    rng.shuffle(options)
    return options
