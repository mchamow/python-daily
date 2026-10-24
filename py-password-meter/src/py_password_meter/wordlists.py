"""The two bundled wordlists, loaded once from inside the package.

- ``eff_large.txt``: the EFF long wordlist, 7776 (= 6**5) words built for dice passphrases.
- ``common_passwords.txt``: the 10,000 most common leaked passwords, most common first.
"""

from functools import cache
from importlib.resources import files

_DIR = files("py_password_meter") / "wordlists"


@cache
def eff_words() -> tuple[str, ...]:
    """The passphrase words. Each line is ``<dice roll>\\t<word>``; we keep only the word."""
    text = (_DIR / "eff_large.txt").read_text(encoding="utf-8")
    return tuple(line.partition("\t")[2] for line in text.splitlines())


@cache
def password_ranks() -> dict[str, int]:
    """Common password -> 1-based popularity rank (``password`` is #1)."""
    text = (_DIR / "common_passwords.txt").read_text(encoding="utf-8")
    ranks: dict[str, int] = {}
    for rank, word in enumerate(text.split(), start=1):
        ranks.setdefault(word.lower(), rank)  # keep the best rank if a word repeats
    return ranks


@cache
def word_ranks() -> dict[str, int]:
    """Everything the meter treats as a dictionary word, with the guesses it costs.

    A common password costs its rank. Any other EFF word costs the size of the EFF list, because
    an attacker who knows you used that list must try every word in it.
    """
    flat = len(eff_words())
    return {word: flat for word in eff_words()} | password_ranks()
