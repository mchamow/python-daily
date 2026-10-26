"""Load a trip's expenses from CSV and work out what everyone paid, used and is owed.

A trip file is a CSV with `paid_by,amount,description,split` columns. Lines starting with
`#` are comments, and `# key: value` comments set `trip` (its name) and `people` (the roster).

The `split` column says who shared an expense, as space-separated tokens:

    (empty) or all   everyone on the roster, equally
    Ana Ben          just Ana and Ben, equally
    Ana*2 Ben        Ana counts twice (two of the three shares)
    Ana=18.50 all    Ana's share is exactly 18.50; the rest is split among everyone else
    all -Dee         everyone except Dee
"""

import csv
import re
from collections import defaultdict
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from difflib import get_close_matches
from pathlib import Path

from .money import MoneyError, allocate, parse_money

REQUIRED_COLUMNS = {"paid_by", "amount", "split"}
DIRECTIVE = re.compile(r"#\s*(?P<key>\w+)\s*:\s*(?P<value>.*)")
TOKEN = re.compile(
    r"(?P<neg>-)?(?P<name>[^\W\d]\w*)"  # a name: letters first, then letters/digits/_
    r"(?:\*(?P<weight>\d+(?:\.\d+)?)|=(?P<amount>\d+(?:\.\d+)?))?"
)


class LedgerError(ValueError):
    """A trip file we can't make sense of; the message says where and why."""


@dataclass(frozen=True, slots=True)
class Expense:
    line: int
    paid_by: str
    amount: Decimal
    description: str
    exact: Mapping[str, Decimal]  # fixed shares, taken off the top
    weights: Mapping[str, Decimal]  # how the rest is divided
    shares: Mapping[str, Decimal]  # the result, in cents; always sums to `amount`


@dataclass(frozen=True, slots=True)
class Trip:
    name: str
    people: tuple[str, ...]
    expenses: tuple[Expense, ...]

    @property
    def total(self) -> Decimal:
        return sum((e.amount for e in self.expenses), Decimal(0))


@dataclass(slots=True)
class Account:
    paid: Decimal = Decimal(0)  # Decimal is immutable, so a shared default is safe
    used: Decimal = Decimal(0)

    @property
    def balance(self) -> Decimal:
        """Positive: the group owes you. Negative: you owe the group."""
        return self.paid - self.used


def _person(name: str, people: Sequence[str]) -> str:
    if name in people:
        return name
    hint = get_close_matches(name, people, n=1)
    did_you_mean = f", did you mean {hint[0]}?" if hint else ""
    raise LedgerError(f"{name!r} isn't on the trip ({', '.join(people)}){did_you_mean}")


def parse_split(
    text: str, amount: Decimal, people: Sequence[str]
) -> tuple[dict[str, Decimal], dict[str, Decimal]]:
    """Read a split column into (exact shares, weights). See the module docstring."""
    exact: dict[str, Decimal] = {}
    weights: dict[str, Decimal] = {}
    excluded: set[str] = set()
    everyone = False

    def claim(name: str) -> str:
        person = _person(name, people)
        if person in exact or person in weights or person in excluded:
            raise LedgerError(f"{person} appears twice in the split")
        return person

    for token in text.split() or ["all"]:
        if not (m := TOKEN.fullmatch(token)):
            raise LedgerError(f"can't read {token!r} in the split")
        # A mapping pattern matches the keys it lists and ignores the rest, so each case
        # reads as "the token has this shape". Order matters: "all" must win over a name.
        match m.groupdict():
            case {"neg": None, "name": "all", "weight": None, "amount": None}:
                everyone = True
            case {"neg": "-", "name": name, "weight": None, "amount": None}:
                excluded.add(claim(name))
            case {"neg": None, "name": name, "weight": None, "amount": None}:
                weights[claim(name)] = Decimal(1)
            case {"neg": None, "name": name, "weight": str(w)}:
                weights[claim(name)] = Decimal(w)
            case {"neg": None, "name": name, "amount": str(a)}:
                exact[claim(name)] = parse_money(a)
            case _:
                raise LedgerError(f"{token!r}: '-' excludes someone, it can't take a share")
    if excluded and not everyone:
        raise LedgerError("'-Name' only makes sense after 'all'")
    if everyone:
        taken = exact.keys() | weights.keys() | excluded
        weights |= {p: Decimal(1) for p in people if p not in taken}
    if any(w == 0 for w in weights.values()):
        raise LedgerError("a weight of 0 means 'not in the split'; leave them out instead")

    rest = amount - sum(exact.values(), Decimal(0))
    if rest < 0:
        raise LedgerError(f"the exact shares add up to more than the expense ({amount})")
    if rest and not weights:
        raise LedgerError(f"the exact shares leave {rest} of {amount} that nobody pays")
    return exact, weights


def shares_of(
    amount: Decimal, exact: Mapping[str, Decimal], weights: Mapping[str, Decimal]
) -> dict[str, Decimal]:
    """Exact shares plus the remainder allocated by weight, cent-exact."""
    rest = amount - sum(exact.values(), Decimal(0))
    shares = dict(exact)
    if weights:
        shares |= zip(weights, allocate(rest, list(weights.values())), strict=True)
    return {name: share for name, share in shares.items() if share}


def _rows(source: str, lines: Iterable[tuple[int, str]]) -> Iterator[tuple[int, dict[str, str]]]:
    """Yield (line number, row) for the data lines; csv sees no comments or blanks."""
    data = [(n, line) for n, line in lines if line.strip() and not line.lstrip().startswith("#")]
    # csv reads any iterable of lines, here a generator; restval fills in short rows
    reader = csv.DictReader((line for _, line in data), restval="")
    missing = REQUIRED_COLUMNS - set(reader.fieldnames or ())
    if missing:
        line = data[0][0] if data else 1
        raise LedgerError(f"{source}:{line}: missing columns {', '.join(sorted(missing))}")
    # data[0] is the header. strict=True would flag a quoted field spanning lines, which we
    # don't support (it would shift every later line number).
    yield from zip((n for n, _ in data[1:]), reader, strict=True)


def load_trip(path: Path) -> Trip:
    """Parse and validate a trip file. Raises LedgerError naming the file and line."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise LedgerError(f"can't read {path}: {e.strerror}") from None
    lines = list(enumerate(text.splitlines(), start=1))
    directives = {
        m["key"].lower(): m["value"].strip()
        for _, line in lines
        if (m := DIRECTIVE.fullmatch(line.strip()))
    }
    rows = list(_rows(path.name, lines))
    if "people" in directives:
        people = tuple(dict.fromkeys(directives["people"].replace(",", " ").split()))
    else:  # roster = everyone named anywhere, in order of first appearance
        names = (
            name
            for _, row in rows
            for token in [row["paid_by"], *row["split"].split()]
            if (m := TOKEN.fullmatch(token.strip())) and (name := m["name"]) != "all"
        )
        people = tuple(dict.fromkeys(names))  # dict keeps insertion order: an ordered set

    expenses: list[Expense] = []
    for n, row in rows:
        try:
            paid_by = _person(row["paid_by"].strip(), people)
            amount = parse_money(row["amount"])
            exact, weights = parse_split(row["split"], amount, people)
        except (LedgerError, MoneyError) as e:
            raise LedgerError(f"{path.name}:{n}: {e}") from None
        description = (row.get("description") or "").strip()
        shares = shares_of(amount, exact, weights)
        expenses.append(Expense(n, paid_by, amount, description, exact, weights, shares))
    if not expenses:
        raise LedgerError(f"{path.name}: no expenses")
    return Trip(directives.get("trip", path.stem), people, tuple(expenses))


def accounts(trip: Trip) -> dict[str, Account]:
    """What each person paid and used. Everyone on the roster appears, in roster order."""
    book: defaultdict[str, Account] = defaultdict(Account)  # a missing key makes an Account()
    for e in trip.expenses:
        book[e.paid_by].paid += e.amount
        for name, share in e.shares.items():
            book[name].used += share
    return {name: book[name] for name in trip.people}


def iou_counts(trip: Trip) -> tuple[int, int]:
    """(one payment per share per expense, one payment per pair of people after netting)."""
    raw = 0
    pairs: defaultdict[tuple[str, str], Decimal] = defaultdict(Decimal)  # Decimal() == 0
    for e in trip.expenses:
        for name, share in e.shares.items():
            if name == e.paid_by:
                continue
            raw += 1
            # key each pair once, alphabetically; the sign says which way the money goes
            a, b = sorted((name, e.paid_by))
            pairs[a, b] += share if a == name else -share
    return raw, sum(1 for owed in pairs.values() if owed)
