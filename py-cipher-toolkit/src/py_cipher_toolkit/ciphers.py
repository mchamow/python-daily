"""The classical ciphers: Caesar, Atbash and Vigenère.

Every cipher here only touches the 52 ASCII letters. Case is kept, and digits, punctuation and
non-English letters (é, ł, ß) pass through unchanged, so a ciphertext keeps the shape of its
plaintext. That makes the output readable, and it is also exactly what lets frequency analysis
break it (see crack.py).
"""

from collections.abc import Iterator
from functools import cache
from itertools import cycle
from string import ascii_letters, ascii_lowercase, ascii_uppercase

LETTERS = frozenset(ascii_letters)


@cache
def shift_table(shift: int) -> dict[int, int]:
    """A `str.translate` table that moves every letter `shift` places along the alphabet.

    There are only 26 distinct tables, and `@cache` builds each one once: Vigenère and the
    cracker ask for the same few tables thousands of times.
    """
    s = shift % 26  # Python's % is never negative here: -3 % 26 == 23 (C# gives -3)
    lower = ascii_lowercase[s:] + ascii_lowercase[:s]
    return str.maketrans(ascii_lowercase + ascii_uppercase, lower + lower.upper())


ATBASH = str.maketrans(
    ascii_lowercase + ascii_uppercase, ascii_lowercase[::-1] + ascii_uppercase[::-1]
)


def caesar(text: str, shift: int) -> str:
    """Shift every letter by `shift`; a negative shift decrypts."""
    return text.translate(shift_table(shift))


def atbash(text: str) -> str:
    """Mirror the alphabet (a↔z, b↔y …). It is its own inverse."""
    return text.translate(ATBASH)


def key_shifts(key: str) -> list[int]:
    """`"Lemon"` → `[11, 4, 12, 14, 13]`. Raises ValueError for anything but ASCII letters."""
    if not key or not LETTERS.issuperset(key):
        raise ValueError(f"a key must be ASCII letters only, got {key!r}")
    return [ascii_lowercase.index(c) for c in key.lower()]


def vigenere(text: str, key: str, *, decrypt: bool = False) -> str:
    """Caesar with a different shift per letter, taken from the key in turn.

    The key only advances on letters, so `"attack at dawn"` under LEMON encrypts the same
    letters as `"ATTACKATDAWN"` does: spaces don't eat key letters.
    """
    sign = -1 if decrypt else 1
    shifts = cycle(sign * s for s in key_shifts(key))

    def chars() -> Iterator[str]:
        for ch in text:
            yield ch.translate(shift_table(next(shifts))) if ch in LETTERS else ch

    return "".join(chars())


def shortest_period(key: str) -> str:
    """`"WALRUSWALRUS"` → `"WALRUS"`: the shortest key that repeats to make this one."""
    n = len(key)
    return next(key[:p] for p in range(1, n + 1) if n % p == 0 and key[:p] * (n // p) == key)
