"""Pattern matchers: each one finds the guessable pieces of a password.

A matcher is a plain function ``str -> Iterator[Match]``, written as a generator. It may report
overlapping matches; strength.py picks the cheapest combination that covers the password.
"""

import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from itertools import groupby, pairwise
from math import comb

from .wordlists import eff_words, password_ranks, word_ranks


@dataclass(frozen=True, slots=True)
class Match:
    start: int
    end: int  # exclusive, like a slice
    token: str
    pattern: str
    guesses: int
    detail: str


# --- dictionary words, capitalised, l33t-speak and reversed ----------------------------------

_LEET = str.maketrans("4@31!|0$57+", "aaeiiiosstt")
_MIN_WORD, _MAX_WORD = 3, 20


def dictionary(password: str) -> Iterator[Match]:
    ranks, common = word_ranks(), password_ranks()
    lower = password.lower()
    for start in range(len(password)):
        for end in range(start + _MIN_WORD, min(len(password), start + _MAX_WORD) + 1):
            token, word = password[start:end], lower[start:end]
            for candidate, how, extra in _spellings(word):
                if (rank := ranks.get(candidate)) is None:
                    continue
                case, variations = _case_variations(token)
                what = (
                    f"common password #{rank:,}"
                    if candidate in common
                    else f"word (one of {len(eff_words()):,})"
                )
                notes = ", ".join(filter(None, [f"{what} '{candidate}'", case, how]))
                yield Match(start, end, token, "dictionary", rank * variations * extra, notes)


def _spellings(word: str) -> Iterator[tuple[str, str, int]]:
    """(candidate, note, extra guesses): the word as typed, un-l33ted and reversed."""
    yield word, "", 1
    if (plain := word.translate(_LEET)) != word:
        swaps = sum(a != b for a, b in zip(word, plain, strict=True))
        yield plain, "l33t", 2**swaps  # each swap is a coin flip a cracker has to try
    yield word[::-1], "reversed", 2


def _case_variations(token: str) -> tuple[str, int]:
    upper = sum(c.isupper() for c in token)
    lower = sum(c.islower() for c in token)
    if upper == 0:
        return "", 1
    if lower == 0:
        return "all caps", 2
    if upper == 1 and token[0].isupper():
        return "capitalised", 2
    # Otherwise: which letters are uppercase? Count the ways to choose them.
    return "mixed case", sum(comb(upper + lower, k) for k in range(1, min(upper, lower) + 1))


# --- years ----------------------------------------------------------------------------------

# A lookahead is zero-width, so finditer can report overlapping years: '19992000' has two.
_YEAR = re.compile(r"(?=(?P<year>19\d\d|20\d\d))")
_MIN_YEAR_SPACE = 20


def year(password: str) -> Iterator[Match]:
    this_year = date.today().year
    for m in _YEAR.finditer(password):
        distance = abs(this_year - int(m["year"]))
        guesses = max(distance, _MIN_YEAR_SPACE)  # recent years are tried first
        yield Match(m.start(), m.start() + 4, m["year"], "year", guesses, "a year")


# --- sequences: abc, 6543, XYZ --------------------------------------------------------------

_OBVIOUS_STARTS = frozenset("aAzZ019")


def sequence(password: str) -> Iterator[Match]:
    start = 0
    # Group neighbouring pairs by the step between them: 'abcx' -> steps 1, 1, 22.
    for step, run in groupby(pairwise(password), key=lambda pair: ord(pair[1]) - ord(pair[0])):
        steps = len(list(run))
        token = password[start : start + steps + 1]
        if step in (1, -1) and len(token) >= 3 and (token.isdigit() or token.isalpha()):
            base = 4 if token[0] in _OBVIOUS_STARTS else 10 if token.isdigit() else 26
            direction = "ascending" if step == 1 else "descending"
            guesses = base * len(token) * (1 if step == 1 else 2)
            yield Match(start, start + len(token), token, "sequence", guesses, direction)
        start += steps


# --- keyboard walks: qwerty, asdf, !@#$ -----------------------------------------------------

_ROWS = ("`1234567890-=", "~!@#$%^&*()_+", "qwertyuiop[]\\", "asdfghjkl;'", "zxcvbnm,./")
_WALKS = _ROWS + tuple(row[::-1] for row in _ROWS)
_KEYS = sum(map(len, _ROWS))


def keyboard(password: str) -> Iterator[Match]:
    lower = password.lower()
    for start in range(len(lower)):
        end = start + 1
        while end < len(lower) and any(lower[start : end + 1] in walk for walk in _WALKS):
            end += 1
        if end - start >= 3:
            token = password[start:end]
            guesses = _KEYS * 2 * (end - start)  # any start key, either direction, any length
            yield Match(start, end, token, "keyboard", guesses, "keys in a row")


# --- separators: the glue in 'correct-horse-battery' -----------------------------------------

_SEPARATORS = " -_.,"


def separator(password: str) -> Iterator[Match]:
    """A common separator: guessing which one costs a little, and it is free after that."""
    for sep in _SEPARATORS:
        positions = [i for i, char in enumerate(password) if char == sep]
        for nth, i in enumerate(positions):
            guesses = len(_SEPARATORS) if nth == 0 else 1
            yield Match(i, i + 1, sep, "separator", guesses, "a common separator")
