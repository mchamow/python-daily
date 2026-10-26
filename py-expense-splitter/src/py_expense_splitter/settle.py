"""Turn balances into transfers: a fast greedy settle-up, and an exact minimum for small groups.

Greedy (biggest debtor pays biggest creditor, repeat) is what most apps do. It never needs
more than n-1 transfers, but it can miss a shortcut: if Ben owes exactly what Cy is owed, they
should settle with each other and leave the rest of the group alone. Finding every such
zero-sum subgroup is the whole problem, and it is NP-hard, so `optimal` searches all subsets
with a bitmask DP: fine for a trip, hopeless for a company.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

MAX_EXACT = 15  # 2**15 subsets * 15 people: well under a second


class UnbalancedError(ValueError):
    """Balances that don't add up to zero: someone's money appeared or vanished."""


@dataclass(frozen=True, slots=True)
class Transfer[N: (Decimal, float) = Decimal]:  # generic, and plain `Transfer` means Decimal
    debtor: str
    creditor: str
    amount: N


def greedy[N: (Decimal, float)](balances: Mapping[str, N]) -> list[Transfer[N]]:
    """Repeatedly settle the biggest debt against the biggest credit.

    Generic so floats.py can run the very same algorithm on float balances.
    """
    open_ = {name: b for name, b in balances.items() if b}
    transfers: list[Transfer[N]] = []
    while len(open_) > 1:
        # min/max with key= pick the entry, not the value; ties go to the first one seen
        debtor = min(open_, key=open_.__getitem__)
        creditor = max(open_, key=open_.__getitem__)
        if not open_[debtor] < 0 < open_[creditor]:  # comparisons chain: a < b and b < c
            break
        amount = min(-open_[debtor], open_[creditor])
        transfers.append(Transfer(debtor, creditor, amount))
        for name, change in ((debtor, amount), (creditor, -amount)):
            open_[name] += change
            if not open_[name]:
                del open_[name]
    return transfers


def optimal(balances: Mapping[str, Decimal]) -> list[Transfer]:
    """The fewest possible transfers: n - (the most zero-sum subgroups we can split into).

    Each subgroup that sums to zero settles internally in (size - 1) transfers, so the more
    groups, the fewer transfers. Over MAX_EXACT people this falls back to greedy.
    """
    if (off := sum(balances.values(), Decimal(0))) != 0:
        raise UnbalancedError(f"balances add up to {off}, not 0")
    names = [name for name, b in balances.items() if b]
    if len(names) > MAX_EXACT:
        return greedy(balances)
    amounts = [balances[name] for name in names]
    n, full = len(names), (1 << len(names)) - 1

    # total[mask] = sum of the balances of the people whose bits are set in mask
    total = [Decimal(0)] * (full + 1)
    for mask in range(1, full + 1):
        low = mask & -mask  # the lowest set bit
        total[mask] = total[mask ^ low] + amounts[low.bit_length() - 1]

    # groups[mask] = the most zero-sum subgroups `mask` can be cut into, built up by adding
    # one person at a time; each time the running set sums to zero, one more group closes.
    groups = [0] * (full + 1)
    for mask in range(1, full + 1):
        best = max(groups[mask ^ (1 << i)] for i in range(n) if mask >> i & 1)
        groups[mask] = best + (total[mask] == 0)  # bool is an int: True + 1 == 2

    # Walk back down the best path. Every zero-sum mask we pass closes a subgroup, and each
    # subgroup is minimal (no zero-sum part inside it), so greedy settles it in size-1 steps.
    transfers: list[Transfer] = []
    mask = boundary = full
    while mask:
        closes = total[mask] == 0
        i = next(
            i
            for i in range(n)
            if mask >> i & 1 and groups[mask ^ (1 << i)] + closes == groups[mask]
        )
        mask ^= 1 << i
        if total[mask] == 0:
            group = boundary ^ mask
            transfers += greedy({names[j]: amounts[j] for j in range(n) if group >> j & 1})
            boundary = mask
    return transfers


def apply[N: (Decimal, float)](
    balances: Mapping[str, N], transfers: list[Transfer[N]]
) -> dict[str, N]:
    """Balances after the transfers; all zero when the plan is right."""
    after = dict(balances)
    for t in transfers:
        after[t.debtor] += t.amount
        after[t.creditor] -= t.amount
    return after
