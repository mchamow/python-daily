# Day 005 · Expense Splitter

`split` reads a trip's expenses from a CSV, works out who owes whom to the cent, and settles up
in the fewest possible transfers. It finds a shortcut that the usual greedy algorithm misses.

## Run it

```bash
cd py-expense-splitter
uv run split data/lisbon.csv                       # balances + the settle-up plan
uv run split data/lisbon.csv --compare             # how many payments each strategy needs
uv run split data/lisbon.csv --floats              # the same maths in float, and what breaks
uv run split data/lisbon.csv -m greedy -c '$'      # greedy plan, dollar signs
uv run split data/typo.csv                         # a mistake, reported with file:line
uv run pytest
```

A trip file is a CSV with `paid_by,amount,description,split` columns. `#` lines are comments,
and `# trip:` / `# people:` comments name the trip and declare who's on it
([data/lisbon.csv](data/lisbon.csv)). The `split` column is a tiny language:

| `split` | means |
| --- | --- |
| *(empty)* or `all` | everyone, equally |
| `Ben Cy Eve` | just those three, equally |
| `Ana*2 Ben Cy` | Ana counts twice (she ate for two) |
| `Cy=12.40 all` | Cy's share is exactly 12.40; everyone splits the rest |
| `all -Dee` | everyone except Dee |

## What it looks like

```text
$ uv run split data/lisbon.csv --compare --floats
Lisbon long weekend · 5 people · 13 expenses · €1,337.90

        paid     used   balance
Ana  €610.50  €273.78  +€336.72
Ben  €460.91  €283.07  +€177.84
Cy   €100.60  €272.22  -€171.62
Dee   €47.80  €225.64  -€177.84
Eve  €118.09  €283.19  -€165.10

Settle up in 3 transfers:
  Dee  →  Ben  €177.84
  Cy   →  Ana  €171.62
  Eve  →  Ana  €165.10

How many payments does it take?
  45  one payment per share of every expense
  10  netted per pair of people
   4  greedy: biggest debtor pays biggest creditor
   3  optimal: zero-sum subgroups settle among themselves

The same trip in float, rounding each share with round(x, 2):
  balances add up to  0.009999999999990905   (Decimal: exactly 0)
  greedy settle-up:
    Dee  →  Ana  177.85000000000002
    Cy   →  Ben  171.62000000000003
    Eve  →  Ana  158.89999999999998
    Eve  →  Ben   6.220000000000027
  …and then Ben is still owed 0.009999999999934062, with nobody left to settle it
```

Two things to notice.

**Ben is owed exactly what Dee owes** (€177.84), so the best plan is for Dee to pay Ben and leave
everyone else out of it. Greedy can't see that. It pairs the biggest debtor (Dee) with the
biggest creditor (Ana), breaks the match, and needs a fourth transfer:

```text
$ uv run split data/lisbon.csv -m greedy
...
Settle up in 4 transfers:
  Dee  →  Ana  €177.84
  Cy   →  Ben  €171.62
  Eve  →  Ana  €158.88
  Eve  →  Ben    €6.22
```

(The sample is tuned so the match exists. In real trips it shows up when part of the group
mostly pays for each other, like a couple or two people on a side trip.)

**The float version invents a cent.** Rounding each share on its own (`Math.round(x * 100) /
100` in JS) means the shares of an expense don't always add up to what was paid. Over 13
expenses, the group ends up charged a cent less than it spent, and Ben is left holding
`0.0099999…` that nobody owes him. The float balances are also off by a few cents per person
(Dee owes 177.85 instead of 177.84), which is why the Dee ↔ Ben shortcut disappears too.

Mistakes in the file get a file:line message:

```text
$ uv run split data/typo.csv
split: typo.csv:4: 'Bn' isn't on the trip (Ana, Ben, Cy), did you mean Ben?
```

## What you'll learn

- **Splitting money without losing a cent**: `Decimal`, `quantize`, and the largest-remainder
  method, with a stable `sorted(key=)` deciding who gets the odd cent
  ([money.py#L27](src/py_expense_splitter/money.py#L27)).
- **`match` with mapping patterns**: each `split` token is parsed by a regex, then matched by
  the *shape* of its `groupdict()` ([ledger.py#L99](src/py_expense_splitter/ledger.py#L99)).
- **`defaultdict` with a dataclass factory**: `defaultdict(Account)` creates accounts on first
  touch, and `defaultdict(Decimal)` is a zero-initialised counter
  ([ledger.py#L193](src/py_expense_splitter/ledger.py#L193)).
- **`csv` reads any iterable of lines**: a generator strips comments before `DictReader` sees
  them, and `zip(strict=True)` keeps the real line numbers
  ([ledger.py#L139](src/py_expense_splitter/ledger.py#L139)).
- **A greedy algorithm and the exact answer**: `min`/`max` with `key=`, then a bitmask dynamic
  programme over all subsets ([settle.py#L28](src/py_expense_splitter/settle.py#L28),
  [settle.py#L50](src/py_expense_splitter/settle.py#L50)).
- **PEP 695 / 696 generics**: one `greedy` for `Decimal` *and* `float`, through a constrained type
  parameter with a default ([settle.py#L22](src/py_expense_splitter/settle.py#L22)).

## Code tour

### 1. Splitting €100 three ways

```python
def allocate(amount: Decimal, weights: Sequence[Decimal]) -> list[Decimal]:
    cents = int(amount / CENT)
    total_weight = sum(weights)
    exact = [cents * w / total_weight for w in weights]
    floors = [int(x) for x in exact]  # int() truncates; the shares are positive, so it floors
    leftover = cents - sum(floors)
    by_remainder = sorted(range(len(exact)), key=lambda i: exact[i] - floors[i], reverse=True)
    for i in by_remainder[:leftover]:
        floors[i] += 1
    return [Decimal(c) * CENT for c in floors]
```

`Decimal` stops `0.1 + 0.2` from being `0.30000000000000004` (day 2 covered that). It does
*not* stop you losing cents: `100.00 / 3` is `33.333…` in any number system, and rounding each
third gives `33.33 × 3 = 99.99`. The fix is to work in whole cents, round everyone down, and
hand the leftover cents to whoever lost the most in rounding. `100.00 / 3` becomes
`[33.34, 33.33, 33.33]`, and the parts always add up to the whole.

Two Python details carry this:

- **`sorted(key=...)` returns indices ordered by a computed value.** There's no
  `IComparer` or comparator `(a, b) => …`; the key function maps each element to something
  comparable, here a `Decimal` remainder. A tuple key sorts by several fields, and
  `render_transfers` uses `key=lambda t: (-t.amount, t.debtor)` for "biggest first, then by name".
- **Python's sort is stable, `reverse=True` included.** Equal remainders keep their input
  order, so the first person listed gets the odd cent every time. Deterministic output is a
  feature when people compare their phones at the airport.

`parse_money` also uses `quantize(CENT)`, which pins the exponent so `Decimal("12.5")` prints
as `12.50`. It rejects anything that `quantize` would change, so `12.345` is an error rather
than a silent rounding.

### 2. A mini-language parsed with mapping patterns

```python
TOKEN = re.compile(
    r"(?P<neg>-)?(?P<name>[^\W\d]\w*)"
    r"(?:\*(?P<weight>\d+(?:\.\d+)?)|=(?P<amount>\d+(?:\.\d+)?))?"
)
...
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
```

Day 2 matched lists, day 4 used guards; this is the third shape `match` understands. A
**mapping pattern** `{"key": pattern}` checks that the key exists and its value matches,
and *ignores keys it doesn't mention*. A literal (`"all"`, `None`, `"-"`) must be equal; a bare
name (`name`) captures; `str(w)` checks the type *and* captures. Cases run top to bottom, so
`all` is tested before the generic name case.

`[^\W\d]\w*` is "a letter, then letters, digits or `_`" in Unicode, so `Zoë` and `Łukasz`
work. `\w` minus `\d` is the usual Python trick for that, since there's no `\p{L}` in `re`.

`claim` is a nested function that closes over `exact`, `weights` and `excluded` to catch
"Ana appears twice". It's a local helper with no class around it, which is often the
Pythonic answer to "this needs a little shared state".

### 3. `defaultdict(Account)`: the ledger in six lines

```python
@dataclass(slots=True)
class Account:
    paid: Decimal = Decimal(0)  # Decimal is immutable, so a shared default is safe
    used: Decimal = Decimal(0)

    @property
    def balance(self) -> Decimal:
        return self.paid - self.used


def accounts(trip: Trip) -> dict[str, Account]:
    book: defaultdict[str, Account] = defaultdict(Account)  # a missing key makes an Account()
    for e in trip.expenses:
        book[e.paid_by].paid += e.amount
        for name, share in e.shares.items():
            book[name].used += share
    return {name: book[name] for name in trip.people}
```

`defaultdict` takes a zero-argument *factory*, not a value. Any callable works: `list`,
`Decimal` (`Decimal()` is `0`), or a dataclass whose fields all have defaults. The first
`book["Ana"]` calls `Account()` and stores it, so `+=` never meets a missing key. In C# that's
`GetValueOrDefault` plus a write-back, or `CollectionsMarshal.GetValueRefOrAddDefault`.

The last line returns a plain `dict` in roster order, so someone who paid nothing and used
nothing still shows up. Reading `book[name]` for them creates their empty `Account`, which is
exactly what we want here, and a classic surprise elsewhere.

### 4. Greedy, then the exact minimum

```python
def greedy[N: (Decimal, float)](balances: Mapping[str, N]) -> list[Transfer[N]]:
    open_ = {name: b for name, b in balances.items() if b}
    transfers: list[Transfer[N]] = []
    while len(open_) > 1:
        debtor = min(open_, key=open_.__getitem__)
        creditor = max(open_, key=open_.__getitem__)
        if not open_[debtor] < 0 < open_[creditor]:
            break
        amount = min(-open_[debtor], open_[creditor])
        ...
```

`min(open_, key=open_.__getitem__)` iterates over the dict's *keys* and compares them by
their values, returning the key: LINQ's `MinBy(kv => kv.Value).Key` in one call.
`a < 0 < b` is a chained comparison, `a < 0 and 0 < b`.

`[N: (Decimal, float)]` is a **constrained** type parameter: `N` is exactly `Decimal` or exactly
`float`, never a mix, which mypy enforces. That lets `floats.py` reuse the same algorithm on
float balances. `Transfer[N: (Decimal, float) = Decimal]` adds a PEP 696 default, so a bare
`Transfer` in the rest of the code means `Transfer[Decimal]`.

Greedy never needs more than *n − 1* transfers, but it isn't optimal. The minimum is
*n − k*, where *k* is the largest number of groups the people can be split into such that each
group's balances add up to zero (each settles internally in size − 1 transfers). Finding *k* is
NP-hard, so `optimal` tries every subset, with each subset encoded as a bitmask:

```python
for mask in range(1, full + 1):
    low = mask & -mask  # the lowest set bit
    total[mask] = total[mask ^ low] + amounts[low.bit_length() - 1]

for mask in range(1, full + 1):
    best = max(groups[mask ^ (1 << i)] for i in range(n) if mask >> i & 1)
    groups[mask] = best + (total[mask] == 0)  # bool is an int: True + 1 == 2
```

`groups[mask]` is the most zero-sum groups the people in `mask` can form. Remove anyone, take
the best of what's left, and add one if this set itself sums to zero. Python's unbounded ints
make bit tricks read like C, and `bool` being an `int` subclass turns the condition into a
counter. Walking back down the table recovers the groups. Five people is 32 subsets; the cap
of 15 is 32,768, still instant. Note that the exactness of `total[mask] == 0` depends on
`Decimal`: with floats, a zero-sum group adds up to `1e-14` and never counts.

### 5. What the float version gets wrong

```python
def float_balances(trip: Trip) -> dict[str, float]:
    net = dict.fromkeys(trip.people, 0.0)
    for e in trip.expenses:
        ...
        for name, weight in e.weights.items():
            # round each share to the cent on its own, like Math.round(x * 100) / 100
            net[name] -= round(rest * float(weight) / total_weight, 2)
```

This is what most quick splitter code does, and every line looks fine. The bug is structural,
not a typo: rounding each share independently means `round(88.10 / 6 * 2, 2) + 4 ×
round(88.10 / 6, 2)` isn't `88.10`. A cent leaks on some expenses, the balances stop summing
to zero, and *someone* ends up owed money nobody owes. The float noise
(`158.89999999999998`) is the visible symptom; the lost cent is the real bug, and it would
happen with `Decimal` too if you rounded per share. `allocate` fixes it by rounding the
*whole split* at once.

## If you wrote this in C# / TypeScript

| Task | C# | TypeScript | Python |
| --- | --- | --- | --- |
| Exact money type | `decimal` (literal `100m`) | none: `number`, or big.js / dinero.js | `Decimal("100")` |
| Round to cents | `Math.Round(x, 2)` (banker's by default) | `Math.round(x * 100) / 100` | `x.quantize(Decimal("0.01"))` (banker's by default) |
| Dictionary with default | `GetValueOrDefault` + assign | `map.get(k) ?? 0` + `set` | `defaultdict(factory)` |
| Sort by computed key | `OrderByDescending(x => …).ThenBy(…)` | `sort((a, b) => …)` | `sorted(xs, key=lambda x: (-x.a, x.b))` |
| Arg-min | `MinBy(kv => kv.Value).Key` | `reduce` by hand | `min(d, key=d.__getitem__)` |
| Numeric generic | `T : INumber<T>` | none | `[N: (Decimal, float)]` |
| Pattern on a dictionary | property patterns on objects, not dictionaries | none | `case {"key": pattern}` |

Splitting an expense equally, side by side:

```csharp
// C#: decimal is exact, but the cent still goes missing
decimal share = Math.Round(100m / 3, 2);       // 33.33
decimal charged = share * 3;                   // 99.99
```

```typescript
// TS: float noise, and the same missing cent
const share = Math.round((100 / 3) * 100) / 100; // 33.33
const charged = share * 3;                       // 99.99
```

```python
parts = allocate(Decimal("100.00"), [Decimal(1)] * 3)
# [Decimal('33.34'), Decimal('33.33'), Decimal('33.33')]: sums to exactly 100.00
```

C# is genuinely nicer for the money type itself: `decimal` is a primitive with a literal
suffix and fast fixed-size arithmetic, while Python spells every constant as
`Decimal("…")` and pays for arbitrary precision. TypeScript has no exact decimal at all
without a library. None of the three fixes the allocation problem for you; that's an
algorithm, and here it's ten lines. Where Python pulls ahead is the surrounding glue:
`defaultdict`, `key=` functions and mapping patterns make the ledger and the parser short.

## Gotchas

- **`sum()` of an empty list of `Decimal`s is the int `0`.** `sum` starts from `0`, so always
  give it a start value: `sum(shares, Decimal(0))`, as the code does. And for floats,
  `sum()` itself has changed: since 3.12 it uses compensated summation, so `sum([0.1] * 10)` is
  `1.0` while a `+=` loop gives `0.9999999999999999`. That's why the float demo prints two
  slightly different residues: the same numbers, added in a different way.
- **`round()` is banker's rounding on the binary value.** `round(0.125, 2)` is `0.12`
  (round half to even), and `round(2.675, 2)` is `2.67` because the float is really
  `2.67499999…`. For money, use `Decimal.quantize(CENT, rounding=ROUND_HALF_UP)` when you need
  half-up, and never round floats.
- **Without a `# people:` line, a typo is a new person.** The roster is then everyone named in
  the file, so `Bn` silently joins the trip and starts owing money. Declare the roster and the same typo
  becomes `'Bn' isn't on the trip …, did you mean Ben?`.

## Your turn

1. **Easy:** add `split FILE --explain NAME`, which lists every expense where NAME paid or had a
   share (`line`, description, paid, share), then a total line. Check in a test that the
   totals equal `accounts(trip)[NAME]`.
2. **Medium:** multi-currency. Add an optional `currency` column and `# rate: USD 0.92`
   directives (EUR per unit). Convert each amount to the base currency with `Decimal` and
   `quantize(CENT)` *before* `allocate`, so every split stays cent-exact. Report an unknown
   currency as `lisbon.csv:7: no rate for USD`.
3. **Stretch:** rewrite `optimal` top-down: a recursive `best(mask)` decorated with
   `@functools.cache`, returning the most zero-sum groups. Time both versions with
   `time.perf_counter` on random 12-, 14- and 16-person trips, and raise `MAX_EXACT` as far as
   the faster one stays under a second.

## Go deeper

- [`decimal`: `quantize` and rounding modes](https://docs.python.org/3/library/decimal.html#decimal.Decimal.quantize)
- [`collections.defaultdict`](https://docs.python.org/3/library/collections.html#collections.defaultdict)
- [Sorting HOW TO: key functions and stability](https://docs.python.org/3/howto/sorting.html)
- [Mapping patterns in `match`](https://docs.python.org/3/reference/compound_stmts.html#mapping-patterns)
- [PEP 695 type parameters](https://peps.python.org/pep-0695/) and
  [PEP 696 defaults](https://peps.python.org/pep-0696/)
- [Largest remainder method](https://en.wikipedia.org/wiki/Largest_remainders_method): the same
  maths allocates parliament seats
- Local lessons: lesson 02 (collections and comprehensions), lesson 08 (pattern matching),
  lesson 05 (type hints), lesson 13 (stdlib and ecosystem).
