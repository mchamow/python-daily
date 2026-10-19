"""Turning raw text into normalised words."""

import re
from collections.abc import Iterator
from importlib.resources import files

# A word is a run of letters, optionally joined by apostrophes: don't, o'clock, rock'n'roll.
# Python's `re` has no \p{L}; [^\W\d_] ("word chars minus digits and underscore") is the
# idiomatic way to say "any Unicode letter".
_WORD = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)*")

# Typographic apostrophes become ASCII ones so "don\N{RIGHT SINGLE QUOTATION MARK}t" and
# "don't" count as one word. \N{...} spells a character by its Unicode name.
_APOSTROPHES = str.maketrans(
    {
        "\N{RIGHT SINGLE QUOTATION MARK}": "'",
        "\N{LEFT SINGLE QUOTATION MARK}": "'",
        "\N{MODIFIER LETTER APOSTROPHE}": "'",
    }
)

# Shipped inside the package, like an EmbeddedResource in .NET. importlib.resources finds
# it whether the package is a folder on disk, an installed wheel or a zip.
STOP_WORDS: frozenset[str] = frozenset(
    line.strip()
    for line in files(__name__).joinpath("stopwords.txt").read_text("utf-8").splitlines()
    if line.strip() and not line.startswith("#")
)


def words(text: str) -> Iterator[str]:
    """Yield casefolded words lazily, so a huge input never becomes one giant list."""
    for match in _WORD.finditer(text.translate(_APOSTROPHES)):
        # casefold() is the Unicode-correct lower(): "Straße" -> "strasse".
        yield match.group().casefold()
