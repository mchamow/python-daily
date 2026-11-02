"""Breaking the ciphers without the key, by frequency analysis.

The whole attack is two ideas:

1. Caesar is broken by trying all 26 shifts and keeping the one whose letters look most like
   English (lowest chi-squared).
2. Vigenère with an n-letter key is just n Caesar ciphers interleaved: letters 0, n, 2n … share
   one shift, letters 1, n+1 … the next. In Python that column is the slice `letters[i::n]`.
   Guess n with the index of coincidence (each column looks like English only at the right n),
   then break each column as a Caesar cipher.

Caesar is Vigenère with a 1-letter key, so one code path handles both.
"""

from collections import Counter
from dataclasses import dataclass
from statistics import fmean
from string import ascii_uppercase
from typing import Literal

from .analysis import chi_squared, index_of_coincidence, letters_only
from .ciphers import atbash, caesar, shift_table, shortest_period, vigenere

type CipherName = Literal["caesar", "vigenere", "atbash"]

MIN_PER_COLUMN = 5  # fewer letters than this per column and the statistics are noise


@dataclass(frozen=True, slots=True)
class Crack:
    """One guess at the plaintext."""

    cipher: CipherName
    key: str  # "D" for Caesar shift 3, "WALRUS" for Vigenère, "" for Atbash
    plaintext: str
    score: float  # chi-squared of the plaintext's letters: lower is more English

    def describe(self) -> str:
        match self.cipher:
            case "caesar" if self.key == "A":
                return "not encrypted (Caesar shift 0)"
            case "caesar":
                shift = ascii_uppercase.index(self.key)
                return f"Caesar, shift {shift} (decrypt with -s {-shift})"
            case "vigenere":
                return f"Vigenère, key {self.key}"
            case "atbash":
                return "Atbash"


@dataclass(frozen=True, slots=True)
class Report:
    candidates: list[Crack]  # best first
    key_lengths: dict[int, float]  # key length → mean index of coincidence of its columns
    key_length: int  # the length the cracker settled on

    @property
    def best(self) -> Crack:
        return self.candidates[0]


def rank_shifts(letters: str) -> list[tuple[int, float]]:
    """Every shift 0-25 with the chi-squared of undoing it, most English first."""
    # translate() runs in C, so 26 full passes over the column are still instant.
    scores = {s: chi_squared(Counter(letters.translate(shift_table(-s)))) for s in range(26)}
    return sorted(scores.items(), key=lambda item: item[1])


def key_length_scores(letters: str, max_length: int) -> dict[int, float]:
    """For each candidate key length n, the mean index of coincidence of the n columns."""
    longest = min(max_length, len(letters) // MIN_PER_COLUMN)
    return {
        n: fmean(index_of_coincidence(letters[i::n]) for i in range(n))
        for n in range(1, max(longest, 1) + 1)
    }


def likely_key_length(scores: dict[int, float], tolerance: float = 0.9) -> int:
    """The *shortest* length that scores within `tolerance` of the best.

    Multiples of the real length score just as well (a 12-letter guess at a 6-letter key still
    gives pure columns), and with fewer letters per column they get luckier, so taking the
    maximum would often pick 12 or 18 instead of 6.
    """
    best = max(scores.values())
    return next(n for n, score in scores.items() if score >= best * tolerance)


def _undo(text: str, letters: str, length: int) -> Crack:
    shifts = [rank_shifts(letters[i::length])[0][0] for i in range(length)]
    key = shortest_period("".join(ascii_uppercase[s] for s in shifts))
    plaintext = vigenere(text, key, decrypt=True)
    score = chi_squared(Counter(letters_only(plaintext)))
    return Crack("caesar" if len(key) == 1 else "vigenere", key, plaintext, score)


def crack(text: str, *, max_key_length: int = 20) -> Report:
    """Guess how `text` was encrypted. Raises ValueError if it has no letters to work with."""
    letters = letters_only(text)
    if len(letters) < 2:
        raise ValueError("there are no letters to analyse")

    scores = key_length_scores(letters, max_key_length)
    length = likely_key_length(scores)
    found = [_undo(text, letters, length)]
    # The runner-up Caesar shifts are worth showing: on short texts the right one often comes 2nd.
    for shift, score in rank_shifts(letters)[:3]:
        found.append(Crack("caesar", ascii_uppercase[shift], caesar(text, -shift), score))
    mirrored = atbash(text)
    found.append(Crack("atbash", "", mirrored, chi_squared(Counter(letters_only(mirrored)))))

    unique = {(c.cipher, c.key): c for c in found}.values()  # dicts keep insertion order
    return Report(sorted(unique, key=lambda c: c.score), scores, length)
