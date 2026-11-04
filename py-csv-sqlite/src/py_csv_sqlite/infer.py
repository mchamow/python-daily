"""Column type inference: classify every cell, widen per column, then convert for SQLite.

Each column's type moves up a small lattice as values arrive:

    INTEGER ─► REAL ─┐
    BOOLEAN ─────────┤
    DATE ─► DATETIME ┴─► TEXT

Anything that isn't on the same path widens straight to TEXT.
"""

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum


class Kind(StrEnum):
    """A column's logical type. SQLite only stores INTEGER, REAL and TEXT (see `storage`)."""

    INTEGER = "integer"
    REAL = "real"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    TEXT = "text"

    @property
    def storage(self) -> str:
        match self:
            case Kind.INTEGER | Kind.BOOLEAN:
                return "INTEGER"
            case Kind.REAL:
                return "REAL"
            case Kind.DATE | Kind.DATETIME | Kind.TEXT:
                return "TEXT"


# Hand-written patterns instead of try: int(s). int() and float() are far too forgiving for
# inference: they accept "1_000", " 12 ", "nan", "inf" and Arabic-Indic digits like "١٢٣".
# [0-9], not \d: in a str pattern \d matches every Unicode decimal digit.
_INTEGER = re.compile(r"[+-]?(?:0|[1-9][0-9]*)")  # no leading zeros: "007" is a code, not 7
_REAL = re.compile(r"[+-]?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_DATETIME = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}(?::[0-9]{2}(?:\.[0-9]{1,6})?)?"
    r"(?:Z|[+-][0-9]{2}:[0-9]{2})?"
)
_TRUE = frozenset({"true", "yes"})
_FALSE = frozenset({"false", "no"})

# Pairs that widen to something narrower than TEXT. frozenset keys make the lookup
# order-independent: widen(REAL, INTEGER) and widen(INTEGER, REAL) hit the same entry.
_WIDER = {
    frozenset({Kind.INTEGER, Kind.REAL}): Kind.REAL,
    frozenset({Kind.DATE, Kind.DATETIME}): Kind.DATETIME,
}


def _is_valid(parse: type[date] | type[datetime], text: str) -> bool:
    try:
        parse.fromisoformat(text)  # the regex checks the shape, this checks the calendar
    except ValueError:
        return False
    return True


def classify(raw: str) -> Kind | None:
    """The narrowest kind that fits one cell, or None for an empty cell."""
    text = raw.strip()
    if not text:
        return None
    if _INTEGER.fullmatch(text):
        return Kind.INTEGER
    if _REAL.fullmatch(text):
        return Kind.REAL
    if text.casefold() in _TRUE | _FALSE:
        return Kind.BOOLEAN
    if _DATE.fullmatch(text) and _is_valid(date, text):
        return Kind.DATE
    if _DATETIME.fullmatch(text) and _is_valid(datetime, text):
        return Kind.DATETIME
    return Kind.TEXT


def widen(a: Kind | None, b: Kind | None) -> Kind | None:
    """The narrowest kind that holds both (None means "no values yet")."""
    if a is None or a == b:
        return b
    if b is None:
        return a
    return _WIDER.get(frozenset({a, b}), Kind.TEXT)


def convert(kind: Kind, raw: str) -> int | float | str | None:
    """Turn one cell into the Python value sqlite3 binds for it. Empty means NULL."""
    text = raw.strip()
    if not text:
        return None
    match kind:
        case Kind.INTEGER:
            return int(text)
        case Kind.REAL:
            return float(text)
        case Kind.BOOLEAN:
            return int(text.casefold() in _TRUE)  # SQLite has no bool: 1 or 0
        case Kind.DATE:
            return date.fromisoformat(text).isoformat()
        case Kind.DATETIME:
            # "2026-11-04T09:30Z" -> "2026-11-04 09:30:00+00:00", a form SQLite's date
            # functions understand. A bare date in a DATETIME column becomes midnight.
            return datetime.fromisoformat(text).isoformat(sep=" ")
        case Kind.TEXT:
            return raw  # keep text exactly as written, spaces included


@dataclass(slots=True)
class Column:
    """What one pass over the file learned about a column."""

    name: str  # the SQL identifier
    header: str  # the CSV header it came from
    kind: Kind | None = None
    nulls: int = 0
    decided_by: str = ""  # the first value of the final kind: why the column is what it is
    primary_key: bool = False
    _seen: set[str] | None = field(default=None, repr=False)

    @property
    def sql_kind(self) -> Kind:
        return self.kind or Kind.TEXT  # an all-empty column is TEXT

    def add(self, raw: str) -> None:
        kind = classify(raw)
        if kind is None:
            self.nulls += 1
            return
        wider = widen(self.kind, kind)
        if wider != self.kind:
            self.kind, self.decided_by = wider, raw.strip()
        if self._seen is not None:
            self._seen.add(raw.strip())


def infer(columns: Sequence[Column], rows: Iterable[Sequence[str]]) -> int:
    """Feed every row through its columns; return the row count.

    A column named `id` that ends up a unique, never-empty INTEGER becomes the primary key.
    Only that column remembers its values, so memory stays flat however big the file is.
    """
    for column in columns:
        column._seen = set() if column.name == "id" else None
    count = 0
    for row in rows:
        count += 1
        for column, cell in zip(columns, row, strict=True):
            column.add(cell)
    for column in columns:
        column.primary_key = (
            column._seen is not None
            and column.kind is Kind.INTEGER
            and column.nulls == 0
            and len(column._seen) == count
        )
        column._seen = None
    return count


def fit(new: Kind | None, declared: str) -> Kind | None:
    """When appending: the kind to convert with so values suit the existing column, or None.

    `declared` is SQLite's storage type from `pragma_table_info`.
    """
    match declared.upper(), new:
        case _, None:
            return Kind.TEXT  # every cell is empty, so every value is NULL whatever the kind
        case "TEXT", Kind.DATE | Kind.DATETIME:
            return new  # still normalised, and the column's CHECK has the final say
        case "TEXT", _:
            return Kind.TEXT  # "02134" must not become 2134 because this file looks numeric
        case "REAL", Kind.INTEGER | Kind.REAL:
            return Kind.REAL
        case "INTEGER", Kind.INTEGER | Kind.BOOLEAN:
            return new
        case _:
            return None
