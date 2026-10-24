"""Estimate how many guesses a password takes when a cracker attacks it cleverly.

The naive formula, ``length * log2(pool)``, assumes every character was picked at random. Real
crackers try common passwords, words, years and keyboard walks first. So we find every such
pattern, then pick the cheapest way to cover the whole password with them: a shortest-path
search over character positions, where a match costs its guesses and any leftover character
costs a full brute-force pool.
"""

import math
import re
import string
from bisect import bisect
from collections import defaultdict
from collections.abc import Callable, Iterator
from dataclasses import dataclass, replace
from operator import itemgetter

from .matchers import Match, dictionary, keyboard, separator, sequence, year

_CLASSES = (string.ascii_lowercase, string.ascii_uppercase, string.digits, string.punctuation + " ")
_NON_ASCII_POOL = 100  # a rough allowance for accents, Cyrillic, emoji, ...

RATINGS = ("very weak", "weak", "fair", "strong", "very strong")
_RATING_BITS = (28, 40, 60, 80)  # 2**80 guesses at 10 billion a second is 3.8 million years

SCENARIOS: dict[str, float] = {  # guesses per second
    "online, throttled (100/hour)": 100 / 3600,
    "online, unthrottled (10/s)": 10,
    "offline, slow hash (10k/s)": 1e4,
    "offline, fast hash (10B/s)": 1e10,
}

_TIPS = {
    "dictionary": "Common passwords and words go first; capitals and l33t swaps barely help.",
    "year": "Years are among the first things a cracker appends.",
    "sequence": "Sequences like abc or 9876 add almost nothing.",
    "keyboard": "Keyboard walks like qwerty or 1qaz are in every cracking list.",
    "repeat": "Repeating a chunk costs a cracker one extra guess per repetition count.",
}


@dataclass(frozen=True, slots=True)
class Estimate:
    password: str
    guesses: int  # a Python int: exact, never overflows, even for a 100-char password
    segments: tuple[Match, ...]
    pool: int

    @property
    def bits(self) -> float:
        return math.log2(self.guesses)

    @property
    def naive_bits(self) -> float:
        return len(self.password) * math.log2(self.pool) if self.password else 0.0

    @property
    def score(self) -> int:
        """0 (very weak) to 4 (very strong). ``bisect`` turns the thresholds into a lookup."""
        return bisect(_RATING_BITS, self.bits)

    @property
    def rating(self) -> str:
        return RATINGS[self.score]

    def crack_times(self) -> dict[str, float]:
        """Seconds to try every candidate up to this one, per attack scenario."""
        return {name: self.guesses / rate for name, rate in SCENARIOS.items()}

    def tips(self) -> list[str]:
        found = dict.fromkeys(m.pattern for m in self.segments)  # a set that keeps order
        tips = [_TIPS[pattern] for pattern in found if pattern in _TIPS]
        if self.score < 3:
            tips.append("Try 'pw phrase': six random words are ~77 bits and easy to type.")
        return tips


def pool_size(password: str) -> int:
    """The brute-force alphabet: every character class the password touches."""
    size = sum(len(chars) for chars in _CLASSES if not set(chars).isdisjoint(password))
    return size + (0 if password.isascii() else _NON_ASCII_POOL)


def estimate(password: str) -> Estimate:
    pool = pool_size(password)
    ending_at: defaultdict[int, list[Match]] = defaultdict(list)
    for matcher in MATCHERS:
        for match in matcher(password):
            ending_at[match.end].append(match)

    # best[i] is the cheapest (guesses, segments) covering password[:i]. Matches are listed
    # before brute force, and min() keeps the first of equals, so a named pattern wins ties.
    best: list[tuple[int, tuple[Match, ...]]] = [(1, ())]
    for end in range(1, len(password) + 1):
        options = [(best[m.start][0] * m.guesses, (*best[m.start][1], m)) for m in ending_at[end]]
        guesses, segments = best[end - 1]
        char = Match(end - 1, end, password[end - 1], "bruteforce", pool, "")
        options.append((guesses * pool, (*segments, char)))
        best.append(min(options, key=itemgetter(0)))

    guesses, segments = best[-1]
    return Estimate(password, guesses, _merge_bruteforce(segments, pool), pool)


def _merge_bruteforce(segments: tuple[Match, ...], pool: int) -> tuple[Match, ...]:
    """Join neighbouring single brute-force characters into one segment for display."""
    merged: list[Match] = []
    for seg in segments:
        if merged and seg.pattern == merged[-1].pattern == "bruteforce":
            prev = merged.pop()
            seg = replace(
                prev, end=seg.end, token=prev.token + seg.token, guesses=prev.guesses * pool
            )
        merged.append(seg)
    return tuple(
        replace(seg, detail=f"{_plural(len(seg.token), 'random char')} from a pool of {pool}")
        if seg.pattern == "bruteforce"
        else seg
        for seg in merged
    )


# --- repeats: the one recursive matcher, so it lives next to estimate() ----------------------

_REPEAT = re.compile(r"(?P<unit>.+?)(?P=unit)+", re.DOTALL)


def repeat(password: str) -> Iterator[Match]:
    for m in _REPEAT.finditer(password):
        unit = m["unit"]
        times = len(m[0]) // len(unit)
        guesses = estimate(unit).guesses * times  # guess the unit, then how many times
        yield Match(m.start(), m.end(), m[0], "repeat", guesses, f"'{unit}', {times} times")


MATCHERS: tuple[Callable[[str], Iterator[Match]], ...] = (
    dictionary,
    sequence,
    keyboard,
    year,
    separator,
    repeat,
)


_YEAR = 365.2425 * 86400
_UNIVERSE_YEARS = 13.8e9
_UNITS = (
    ("year", _YEAR),
    ("month", _YEAR / 12),
    ("day", 86400.0),
    ("hour", 3600.0),
    ("minute", 60.0),
    ("second", 1.0),
)


def human_duration(seconds: float) -> str:
    if seconds < 1:
        return "under a second"
    years = seconds / _YEAR
    if years >= _UNIVERSE_YEARS:
        return "longer than the universe has existed"
    for word, size in (("billion", 1e9), ("million", 1e6), ("thousand", 1e3)):
        if years >= size:
            return f"{years / size:.0f} {word} years"
    for unit, length in _UNITS:
        if seconds >= length:
            return _plural(round(seconds / length), unit)
    raise AssertionError("unreachable: every value >= 1 matches 'second'")


def _plural(n: int, noun: str) -> str:
    return f"{n} {noun}" if n == 1 else f"{n} {noun}s"
