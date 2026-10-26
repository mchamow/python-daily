"""Money as exact Decimal cents: parsing, splitting without losing a cent, and formatting."""

from collections.abc import Sequence
from decimal import Decimal, InvalidOperation

CENT = Decimal("0.01")


class MoneyError(ValueError):
    """An amount that isn't a positive number of whole cents."""


def parse_money(text: str) -> Decimal:
    """Parse '12.5' or '1234.56' into an exact Decimal; never via float."""
    try:
        value = Decimal(text.strip())
    except InvalidOperation:
        raise MoneyError(f"{text!r} is not an amount") from None
    if not value.is_finite() or value <= 0:
        raise MoneyError(f"{text!r} must be a positive amount")
    if value != value.quantize(CENT):
        raise MoneyError(f"{text!r} has fractions of a cent")
    # quantize pins the exponent to -2, so 12.5 prints as 12.50 from here on
    return value.quantize(CENT)


def allocate(amount: Decimal, weights: Sequence[Decimal]) -> list[Decimal]:
    """Split `amount` in proportion to `weights` so the parts add up to it exactly.

    Everyone gets their share rounded down to the cent, then the cents that are left
    over go to the largest remainders: the "largest remainder" method. 100.00 / 3 is
    33.34 + 33.33 + 33.33, never 33.33 * 3 = 99.99.
    """
    if not weights or any(w <= 0 for w in weights):
        raise MoneyError("need at least one positive weight to split by")
    cents = int(amount / CENT)
    total_weight = sum(weights)
    exact = [cents * w / total_weight for w in weights]
    floors = [int(x) for x in exact]  # int() truncates; the shares are positive, so it floors
    leftover = cents - sum(floors)
    # sorted() is stable: equal remainders keep their input order, so the result is
    # deterministic and the first-listed person picks up the odd cent.
    by_remainder = sorted(range(len(exact)), key=lambda i: exact[i] - floors[i], reverse=True)
    for i in by_remainder[:leftover]:
        floors[i] += 1
    return [Decimal(c) * CENT for c in floors]


def fmt(amount: Decimal, symbol: str = "€", *, sign: bool = False) -> str:
    """Format money: fmt(Decimal('1234.5')) -> '€1,234.50'; sign=True adds '+' or '-'."""
    text = f"{abs(amount):,.2f}"  # Decimal supports the same format mini-language as float
    prefix = ("-" if amount < 0 else "+") if sign else ("-" if amount < 0 else "")
    return f"{prefix}{symbol}{text}"
