"""The same trip in float arithmetic, the way `amount / people.length` does it in JavaScript.

Nothing here is used for the real numbers. It exists to show what goes wrong without Decimal.
"""

from dataclasses import dataclass

from .ledger import Trip
from .settle import Transfer, greedy


@dataclass(frozen=True, slots=True)
class FloatReport:
    balances: dict[str, float]
    residue: float  # what the balances add up to; exactly 0 with Decimal
    transfers: list[Transfer[float]]


def float_balances(trip: Trip) -> dict[str, float]:
    net = dict.fromkeys(trip.people, 0.0)
    for e in trip.expenses:
        amount = float(e.amount)
        net[e.paid_by] += amount
        rest = amount
        for name, share in e.exact.items():
            net[name] -= float(share)
            rest -= float(share)
        total_weight = sum(float(w) for w in e.weights.values())
        for name, weight in e.weights.items():
            # round each share to the cent on its own, like Math.round(x * 100) / 100
            net[name] -= round(rest * float(weight) / total_weight, 2)
    return net


def float_report(trip: Trip) -> FloatReport:
    balances = float_balances(trip)
    residue = 0.0
    for b in balances.values():  # a running +=, like JS reduce; see the README on sum()
        residue += b
    return FloatReport(balances, residue, greedy(balances))
