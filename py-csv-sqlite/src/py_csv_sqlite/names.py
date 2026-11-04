"""CSV headers and file names -> safe, readable SQL identifiers."""

import re
import unicodedata
from collections.abc import Iterable

# Letters NFKD can't split into "base + accent", so they need a hand mapping.
_FOLD = str.maketrans({"ł": "l", "Ł": "L", "ß": "ss", "ø": "o", "Ø": "O", "đ": "d", "æ": "ae"})
_SYMBOLS = str.maketrans({"%": " pct ", "#": " no ", "&": " and "})


def to_identifier(text: str, fallback: str = "column") -> str:
    """'Unit Price ($)' -> 'unit_price', 'Discount %' -> 'discount_pct', 'Zażółć' -> 'zazolc'."""
    text = text.translate(_FOLD).translate(_SYMBOLS)
    ascii_only = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    name = re.sub(r"[^a-z0-9]+", "_", ascii_only.casefold()).strip("_")
    if not name:
        return fallback
    return f"_{name}" if name[0].isdigit() else name


def unique_identifiers(headers: Iterable[str]) -> list[str]:
    """Identifiers for a header row: 'Name', 'name', '' -> 'name', 'name_2', 'column_3'."""
    names: list[str] = []
    for position, header in enumerate(headers, start=1):
        base = to_identifier(header, fallback=f"column_{position}")
        name, n = base, 1
        while name in names:
            n += 1
            name = f"{base}_{n}"
        names.append(name)
    return names


def quote(identifier: str) -> str:
    """Quote an identifier for SQL. `?` placeholders bind values only, never names."""
    return '"' + identifier.replace('"', '""') + '"'
