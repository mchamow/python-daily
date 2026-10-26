from decimal import Decimal
from pathlib import Path

import pytest

from py_expense_splitter.ledger import (
    LedgerError,
    accounts,
    iou_counts,
    load_trip,
    parse_split,
    shares_of,
)

D = Decimal
PEOPLE = ("Ana", "Ben", "Cy", "Dee")
SAMPLE = Path(__file__).parent.parent / "data" / "lisbon.csv"


def split(text: str, amount: str = "100.00") -> dict[str, Decimal]:
    exact, weights = parse_split(text, D(amount), PEOPLE)
    return shares_of(D(amount), exact, weights)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", {"Ana": "25.00", "Ben": "25.00", "Cy": "25.00", "Dee": "25.00"}),
        ("all -Dee", {"Ana": "33.34", "Ben": "33.33", "Cy": "33.33"}),
        ("Ana*3 Ben", {"Ana": "75.00", "Ben": "25.00"}),
        ("Cy=40 all", {"Cy": "40.00", "Ana": "20.00", "Ben": "20.00", "Dee": "20.00"}),
        ("Ana=60 Ben=40", {"Ana": "60.00", "Ben": "40.00"}),
    ],
)
def test_split_syntax(text: str, expected: dict[str, str]) -> None:
    shares = split(text)
    assert shares == {name: D(v) for name, v in expected.items()}
    assert sum(shares.values()) == D("100.00")


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("Ann Ben", "did you mean Ana"),
        ("Ana Ana", "appears twice"),
        ("Ana -Ben", "only makes sense after 'all'"),
        ("Ana=70 Ben=40", "more than the expense"),
        ("Ana=70 Ben=20", "nobody pays"),
        ("Ana*0 Ben", "weight of 0"),
        ("-Ana*2 all", "can't take a share"),
        ("Ana,Ben", "can't read"),
    ],
)
def test_split_errors(text: str, message: str) -> None:
    with pytest.raises(LedgerError, match=message):
        split(text)


def test_sample_trip_balances_to_zero() -> None:
    trip = load_trip(SAMPLE)
    book = accounts(trip)
    assert trip.name == "Lisbon long weekend"
    assert sum(a.paid for a in book.values()) == trip.total == D("1337.90")
    assert sum(a.balance for a in book.values()) == 0
    assert all(sum(e.shares.values()) == e.amount for e in trip.expenses)


def test_roster_from_names_and_comments(tmp_path: Path) -> None:
    trip_file = tmp_path / "dinner.csv"
    trip_file.write_text(
        "# a comment, with a comma\n"
        "paid_by,amount,description,split\n"
        "\n"
        "Ana,90,Dinner,Ana Ben Cy\n"
        "# another comment\n"
        "Ben,15.00,Taxi\n"
    )
    trip = load_trip(trip_file)
    assert trip.people == ("Ana", "Ben", "Cy")
    assert trip.name == "dinner"
    assert [e.line for e in trip.expenses] == [4, 6]  # real line numbers, comments and all
    assert {n: a.balance for n, a in accounts(trip).items()} == {
        "Ana": D("55.00"),
        "Ben": D("-20.00"),
        "Cy": D("-35.00"),
    }
    assert iou_counts(trip) == (4, 3)  # Ana-Ben, Ana-Cy and Ben-Cy each net to one payment


def test_errors_name_file_and_line(tmp_path: Path) -> None:
    trip_file = tmp_path / "bad.csv"
    trip_file.write_text("# people: Ana Ben\npaid_by,amount,split\nAna,10,all\nBen,ten,all\n")
    with pytest.raises(LedgerError, match=r"^bad\.csv:4: 'ten' is not an amount"):
        load_trip(trip_file)
