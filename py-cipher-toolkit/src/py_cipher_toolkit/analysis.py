"""Letter statistics: how English-like is a piece of text?

Two measures, both built on a `Counter` of letters:

* **chi-squared** compares the letter counts with English's. Lower means more English. The
  cracker uses it to pick the right shift.
* **index of coincidence** is the chance that two letters picked at random are the same. It
  doesn't care *which* letter is common, only that some are, so it survives a Caesar shift.
  English scores about 0.066 and uniformly random letters 1/26 ≈ 0.038. The cracker uses it to
  find a Vigenère key's length.
"""

from collections import Counter
from typing import Final

from .ciphers import LETTERS

# Letter frequencies of English text, in per cent (Lewand, "Cryptological Mathematics").
ENGLISH: Final = {
    "a": 8.167, "b": 1.492, "c": 2.782, "d": 4.253, "e": 12.702, "f": 2.228, "g": 2.015,
    "h": 6.094, "i": 6.966, "j": 0.153, "k": 0.772, "l": 4.025, "m": 2.406, "n": 6.749,
    "o": 7.507, "p": 1.929, "q": 0.095, "r": 5.987, "s": 6.327, "t": 9.056, "u": 2.758,
    "v": 0.978, "w": 2.360, "x": 0.150, "y": 1.974, "z": 0.074,
}  # fmt: skip
ENGLISH_IOC: Final = sum((p / 100) ** 2 for p in ENGLISH.values())  # ≈ 0.0655
RANDOM_IOC: Final = 1 / 26


def letters_only(text: str) -> str:
    """The ASCII letters of `text`, lowercased: `"Zażółć, Wörld!"` → `"zawrld"`."""
    # Filter *before* lowering: "İ".lower() is two characters, "i" plus a combining dot.
    return "".join(c for c in text if c in LETTERS).lower()


def chi_squared(counts: Counter[str]) -> float:
    """How far these letter counts are from English. 0 is a perfect match."""
    n = counts.total()
    if n == 0:
        return float("inf")
    return sum((counts[c] - n * p / 100) ** 2 / (n * p / 100) for c, p in ENGLISH.items())


def index_of_coincidence(letters: str) -> float:
    """The probability that two letters drawn without replacement are equal."""
    n = len(letters)
    if n < 2:
        return 0.0
    return sum(k * (k - 1) for k in Counter(letters).values()) / (n * (n - 1))


def frequencies(text: str) -> dict[str, float]:
    """Per-cent frequency of each of the 26 letters, zeros included, in a-z order."""
    counts = Counter(letters_only(text))
    n = counts.total() or 1
    return {c: 100 * counts[c] / n for c in ENGLISH}
