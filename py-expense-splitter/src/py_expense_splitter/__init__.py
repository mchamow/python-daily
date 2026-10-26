"""split: who owes whom after a trip, settled exactly and in the fewest transfers."""

import argparse
import sys
from collections.abc import Callable, Mapping, Sequence
from decimal import Decimal
from pathlib import Path

from .floats import float_report
from .ledger import LedgerError, Trip, accounts, iou_counts, load_trip
from .money import fmt
from .settle import Transfer, apply, greedy, optimal

type Settler = Callable[[Mapping[str, Decimal]], list[Transfer]]
METHODS: dict[str, Settler] = {"optimal": optimal, "greedy": greedy}


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        trip = load_trip(args.file)
    except LedgerError as error:
        print(f"split: {error}", file=sys.stderr)
        return 1
    symbol: str = args.currency  # Namespace attributes are Any: pin the type at the edge
    balances = {name: account.balance for name, account in accounts(trip).items()}
    transfers = METHODS[args.method](balances)

    sections = [render_summary(trip, symbol), render_transfers(transfers, symbol)]
    if args.compare:
        sections.append(render_compare(trip, balances))
    if args.floats:
        sections.append(render_floats(trip))
    print("\n\n".join(sections))
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="split", description=__doc__, suggest_on_error=True)
    parser.add_argument("file", type=Path, help="trip CSV: paid_by,amount,description,split")
    parser.add_argument(
        "-m", "--method", choices=METHODS, default="optimal", help="settle-up algorithm"
    )
    parser.add_argument("-c", "--currency", default="€", help="symbol to print (default: €)")
    parser.add_argument("--compare", action="store_true", help="count transfers per strategy")
    parser.add_argument("--floats", action="store_true", help="redo the maths in float")
    return parser


def _table(rows: Sequence[tuple[str, ...]], indent: str = "") -> list[str]:
    """Left-align the first column, right-align the rest."""
    # zip(*rows) transposes rows into columns, so each width is one max() per column
    widths = [max(map(len, column)) for column in zip(*rows, strict=True)]
    return [
        indent
        + "  ".join(
            cell.ljust(w) if i == 0 else cell.rjust(w)
            for i, (cell, w) in enumerate(zip(row, widths, strict=True))
        )
        for row in rows
    ]


def render_summary(trip: Trip, symbol: str) -> str:
    title = (
        f"{trip.name} · {len(trip.people)} people · {len(trip.expenses)} expenses · "
        f"{fmt(trip.total, symbol)}"
    )
    rows = [("", "paid", "used", "balance")]
    rows += [
        (name, fmt(a.paid, symbol), fmt(a.used, symbol), fmt(a.balance, symbol, sign=True))
        for name, a in accounts(trip).items()
    ]
    return "\n".join([title, "", *_table(rows)])


def render_transfers(transfers: list[Transfer], symbol: str) -> str:
    if not transfers:
        return "Everyone is square."
    # biggest first: -amount sorts descending, and the name breaks ties
    ordered = sorted(transfers, key=lambda t: (-t.amount, t.debtor))
    rows = [(t.debtor, "→", t.creditor, fmt(t.amount, symbol)) for t in ordered]
    plural = "transfer" if len(transfers) == 1 else "transfers"
    return "\n".join([f"Settle up in {len(transfers)} {plural}:", *_table(rows, "  ")])


def render_compare(trip: Trip, balances: dict[str, Decimal]) -> str:
    raw, pairwise = iou_counts(trip)
    rows = [
        (raw, "one payment per share of every expense"),
        (pairwise, "netted per pair of people"),
        (len(greedy(balances)), "greedy: biggest debtor pays biggest creditor"),
        (len(optimal(balances)), "optimal: zero-sum subgroups settle among themselves"),
    ]
    return "\n".join(["How many payments does it take?"] + [f"{n:>4}  {how}" for n, how in rows])


def render_floats(trip: Trip) -> str:
    report = float_report(trip)
    lines = [
        "The same trip in float, rounding each share with round(x, 2):",
        f"  balances add up to  {report.residue!r}   (Decimal: exactly 0)",
        "  greedy settle-up:",
        *_table([(t.debtor, "→", t.creditor, repr(t.amount)) for t in report.transfers], "    "),
    ]
    for name, left in apply(report.balances, report.transfers).items():
        if left:
            owed = f"is still owed {left!r}" if left > 0 else f"still owes {-left!r}"
            lines.append(f"  …and then {name} {owed}, with nobody left to settle it")
    return "\n".join(lines)
