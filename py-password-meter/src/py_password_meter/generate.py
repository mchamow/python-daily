"""Random passwords and passphrases, with the exact entropy of the process that made them.

All randomness comes from ``secrets``, which reads the OS CSPRNG. The ``random`` module is a
Mersenne Twister: fine for games, predictable after 624 outputs, so never use it for secrets.
"""

import math
import secrets
import string
from dataclasses import dataclass
from itertools import combinations

from .wordlists import eff_words

CLASSES: dict[str, str] = {
    "lower": string.ascii_lowercase,
    "upper": string.ascii_uppercase,
    "digits": string.digits,
    "symbols": string.punctuation,
}
AMBIGUOUS = frozenset("Il1|O0o`'\"")  # easy to misread when someone types it from a screen


@dataclass(frozen=True, slots=True)
class Secret:
    text: str
    bits: float
    recipe: str


def password(
    length: int = 20, classes: tuple[str, ...] = tuple(CLASSES), *, unambiguous: bool = False
) -> Secret:
    """A password with at least one character from every requested class."""
    if not classes:
        raise ValueError("pick at least one character class")
    if length < len(classes):
        raise ValueError(f"length {length} can't fit one of each of {len(classes)} classes")
    pools = [
        "".join(c for c in CLASSES[name] if not (unambiguous and c in AMBIGUOUS))
        for name in classes
    ]
    alphabet = "".join(pools)

    # Rejection sampling: draw uniformly, throw away draws that miss a class. Every valid password
    # stays equally likely, unlike "pick one of each, then shuffle", which skews the distribution.
    while True:
        text = "".join(secrets.choice(alphabet) for _ in range(length))
        if all(not set(pool).isdisjoint(text) for pool in pools):
            break

    count = count_valid(length, [len(pool) for pool in pools])
    recipe = f"{length} chars, {len(alphabet)}-symbol alphabet, every class present"
    return Secret(text, math.log2(count), recipe)


def count_valid(length: int, sizes: list[int]) -> int:
    """How many strings of ``length`` contain at least one character from each pool.

    Inclusion-exclusion: all strings, minus those missing one pool, plus those missing two, ...
    Python ints never overflow, so this is exact even at 94**100.
    """
    total = sum(sizes)
    return sum(
        (-1) ** k * (total - sum(missing)) ** length
        for k in range(len(sizes) + 1)
        for missing in combinations(sizes, k)
    )


def passphrase(
    words: int = 6, *, separator: str = "-", capitalize: bool = False, number: bool = False
) -> Secret:
    """Words drawn uniformly from the EFF list: 6 words is ~77.5 bits and easy to type."""
    if words < 1:
        raise ValueError("a passphrase needs at least one word")
    wordlist = eff_words()
    chosen = [secrets.choice(wordlist) for _ in range(words)]
    bits = words * math.log2(len(wordlist))
    recipe = f"{words} words from a {len(wordlist):,}-word list"

    # Capitalising every word is a fixed rule, so it adds zero bits: the attacker knows it too.
    if capitalize:
        chosen = [word.capitalize() for word in chosen]
    if number:
        where = secrets.randbelow(words)
        chosen[where] += str(secrets.randbelow(10))
        bits += math.log2(10 * words)
        recipe += ", plus a digit on a random word"
    return Secret(separator.join(chosen), bits, recipe)
