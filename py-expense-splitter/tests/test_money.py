from decimal import Decimal

import pytest

from py_expense_splitter.money import MoneyError, allocate, fmt, parse_money

D = Decimal


@pytest.mark.parametrize(
    ("amount", "weights", "expected"),
    [
        ("100.00", [1, 1, 1], ["33.34", "33.33", "33.33"]),
        ("0.02", [1, 1, 1], ["0.01", "0.01", "0.00"]),
        ("10.00", [2, 1], ["6.67", "3.33"]),
        ("88.10", [2, 1, 1, 1, 1], ["29.37", "14.69", "14.68", "14.68", "14.68"]),
        ("1.00", [D("0.5"), D("0.25"), D("0.25")], ["0.50", "0.25", "0.25"]),
    ],
)
def test_allocate_never_loses_a_cent(
    amount: str, weights: list[Decimal | int], expected: list[str]
) -> None:
    parts = allocate(D(amount), [D(w) for w in weights])
    assert parts == [D(e) for e in expected]
    assert sum(parts) == D(amount)


@pytest.mark.parametrize("text", ["abc", "0", "-5", "12.345", "NaN", "Infinity", ""])
def test_parse_money_rejects(text: str) -> None:
    with pytest.raises(MoneyError):
        parse_money(text)


def test_parse_money_pins_two_places() -> None:
    assert str(parse_money(" 12.5 ")) == "12.50"


def test_fmt() -> None:
    assert fmt(D("1234.5")) == "€1,234.50"
    assert fmt(D("-3"), "$", sign=True) == "-$3.00"
    assert fmt(D("3"), sign=True) == "+€3.00"
