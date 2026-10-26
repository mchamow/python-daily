import random
from decimal import Decimal

import pytest

from py_expense_splitter.settle import UnbalancedError, apply, greedy, optimal

D = Decimal

# Ben's credit exactly matches Dee's debt, but greedy pairs Dee with Ana first
TRICKY = {"Ana": D(100), "Ben": D(70), "Cy": D(-50), "Dee": D(-70), "Eve": D(-50)}


def test_greedy_misses_the_shortcut_optimal_finds() -> None:
    assert len(greedy(TRICKY)) == 4
    plan = optimal(TRICKY)
    assert len(plan) == 3
    assert any((t.debtor, t.creditor, t.amount) == ("Dee", "Ben", D(70)) for t in plan)


def random_balances(rng: random.Random, n: int) -> dict[str, Decimal]:
    # small whole amounts make zero-sum subgroups common, which is the hard case
    amounts = [D(rng.randint(-9, 9)) for _ in range(n - 1)]
    amounts.append(-sum(amounts, D(0)))
    return {f"p{i}": a for i, a in enumerate(amounts)}


@pytest.mark.parametrize("seed", range(40))
def test_plans_always_settle_and_optimal_never_loses(seed: int) -> None:
    balances = random_balances(random.Random(seed), n=random.Random(seed).randint(2, 9))
    fast, best = greedy(balances), optimal(balances)
    for plan in (fast, best):
        assert all(v == 0 for v in apply(balances, plan).values())
        assert all(t.amount > 0 for t in plan)
    assert len(best) <= len(fast) <= max(len([b for b in balances.values() if b]) - 1, 0)


def test_everyone_square() -> None:
    assert optimal({"Ana": D(0), "Ben": D(0)}) == []


def test_unbalanced_is_refused() -> None:
    with pytest.raises(UnbalancedError, match=r"add up to 0\.01"):
        optimal({"Ana": D("10.01"), "Ben": D("-10.00")})


def test_greedy_works_on_floats_too() -> None:
    plan = greedy({"Ana": 0.1 + 0.2, "Ben": -0.3})
    assert [(t.debtor, t.creditor) for t in plan] == [("Ben", "Ana")]
    left = apply({"Ana": 0.1 + 0.2, "Ben": -0.3}, plan)
    assert left["Ana"] != 0  # 0.30000000000000004 - 0.3: the float residue that never clears
