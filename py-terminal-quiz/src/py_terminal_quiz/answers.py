"""Judge a typed answer, and turn a correct one into points (faster and harder pays more)."""

import re
import unicodedata
from difflib import SequenceMatcher
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # only for the annotations: questions.py imports this module at runtime
    from .questions import Difficulty, Question

TYPO_RATIO = 0.85  # how similar a free-text answer must be to count despite a typo
STREAK_BONUS, STREAK_CAP = 100, 500
MULTIPLIER = {"easy": 1.0, "medium": 1.5, "hard": 2.0}


class Verdict(Enum):
    CORRECT = "correct"
    TYPO = "correct, with a typo"
    WRONG = "wrong"
    SLOW = "too slow"
    SKIPPED = "skipped"

    @property
    def scores(self) -> bool:
        return self in {Verdict.CORRECT, Verdict.TYPO}


def normalize(text: str) -> str:
    """'  Reykjavík ' -> 'reykjavik', 'Comma-Separated  values' -> 'comma separated values'."""
    # NFKD splits "í" into "i" + a combining accent; dropping the combining marks drops the
    # accents. casefold() is lower() that also knows "ß" == "ss".
    decomposed = unicodedata.normalize("NFKD", text)
    bare = "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()
    bare = re.sub(r"(?<=\w)-(?=\w)", " ", bare)  # "comma-separated", but keep the sign of "-4"
    return " ".join(re.findall(r"[\w.+-]+", bare))


def judge(question: Question, reply: str, options: list[str]) -> tuple[Verdict, str]:
    """The verdict, and the option the reply resolved to (a letter becomes its option)."""
    reply = reply.strip()
    if not reply:
        return Verdict.SKIPPED, ""
    if options and len(reply) == 1 and reply.isalpha():
        index = ord(reply.upper()) - ord("A")
        if 0 <= index < len(options):
            reply = options[index]
    given = normalize(reply)
    accepted = [normalize(a) for a in question.answers]
    if given in accepted:
        return Verdict.CORRECT, reply
    # Forgive typos only in free-text answers made of letters: "Reykjavic" yes, "1988" no,
    # and a near miss among four printed options is just a wrong pick.
    if not options and any(
        any(c.isalpha() for c in a) and SequenceMatcher(None, given, a).ratio() >= TYPO_RATIO
        for a in accepted
    ):
        return Verdict.TYPO, reply
    return Verdict.WRONG, reply


def points(seconds: float, limit: float, difficulty: Difficulty, streak: int) -> int:
    """1000 for an instant answer, falling to 500 at the buzzer; times difficulty; plus streak.

    ``streak`` counts this answer, so the first right answer in a row earns no bonus.
    """
    if seconds > limit:
        return 0
    speed = 1 - 0.5 * max(seconds, 0) / limit
    bonus = min(STREAK_BONUS * (streak - 1), STREAK_CAP)
    return round(1000 * speed * MULTIPLIER[difficulty]) + max(bonus, 0)
