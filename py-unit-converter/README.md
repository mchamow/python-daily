# Day 002 · Unit Converter REPL

`conv` converts units exactly (`10 km to mi`, `5 ft 11 in to cm`, `98.6 F to C`) and tells you
whether a result is exact (`=`) or was rounded to fit on screen (`≈`).

## Run it

```bash
cd py-unit-converter
uv run conv                        # interactive REPL: type 'help', Ctrl-D to leave
uv run conv 5 ft 11 in to cm       # one-shot
uv run conv 1 mi                   # a quantity in every unit of its dimension
uv run conv units                  # what it knows; 'units volume' for definitions
printf '10 km to mi\n98.6 F to C\n' | uv run conv   # one expression per line from a pipe
uv run pytest
```

It knows 50 units across length, mass, volume (US customary), time, speed, data (both `MB` and
`MiB`) and temperature, with spellings like `km`, `kilometres` and `Kilometers`.

## What it looks like

```text
$ uv run conv
conv: exact unit conversions. Try '10 km to mi', 'help', or Ctrl-D to leave.
> 10 km to mi
10 km ≈ 6.213711922 mi
> 5 ft 11 in to cm
5 ft 11 in = 180.34 cm
> 98.6 F to C
98.6 F = 37 °C
> 1 km/h to m/s
1 km/h ≈ 0.2777777778 m/s  (exactly 5/18)
> 1 tsp to ml
1 tsp ≈ 4.928921594 ml
> digits 20
showing 20 significant digits
> ans to ml
ans = 4.92892159375 ml
> 1 parsec to m
error: unknown unit 'parsec'. Type 'units' to list them.
> 10 kilomter to mi
error: unknown unit 'kilomter'. Did you mean kilometer, kilometers, kilometre?
```

The standout is that `≈` turned into `=` above. The converter never rounds while it calculates.
It rounds only for display, and it *knows* when that display hides digits. A teaspoon is exactly
4.92892159375 ml, all 12 significant digits. At the default 10 digits that's a rounding, so it
says `≈`; at 20 digits nothing is lost, so it says `=`. For a value that never terminates, like
5/18, it shows the exact fraction as well.

Compare that with floats, which is what `double` or a JS `number` gives you:

```text
$ python3 -c "print(0.3048 / 0.0254, 4.35 * 100, (36.6 + 273.15 - 273.15) * 9/5 + 32)"
12.000000000000002 434.99999999999994 97.88000000000004
$ printf '1 ft to in\n4.35 m to cm\n36.6 C to F\n' | uv run conv
1 ft = 12 in
4.35 m = 435 cm
36.6 C = 97.88 °F
```

## What you'll learn

- **Structural pattern matching on lists**: `case [*source, "to" | "as" | "->", target]` parses
  a whole command in one line ([parser.py#L81](src/py_unit_converter/parser.py#L81)).
- **Class patterns and exhaustiveness**: `match` over dataclass commands, with
  `assert_never` making mypy prove that every command is handled
  ([session.py#L45](src/py_unit_converter/session.py#L45)).
- **`Fraction` for exact maths**: every conversion factor and result is a rational number, so
  nothing is rounded until display ([quantity.py#L21](src/py_unit_converter/quantity.py#L21)).
- **`Decimal` contexts and signals**: rounding to N significant digits and *asking* whether
  that lost anything ([quantity.py#L49](src/py_unit_converter/quantity.py#L49)).
- **Dict dispatch instead of a switch**: 50 units and about 170 spellings are one dict lookup,
  plus a `difflib` "did you mean?" ([units.py#L146](src/py_unit_converter/units.py#L146)).
- **A REPL in the standard library**: `input()` with `readline` history, Ctrl-C/Ctrl-D
  handling, and a batch mode when stdin is a pipe
  ([\_\_init\_\_.py#L48](src/py_unit_converter/__init__.py#L48)).

## Code tour

### 1. Parsing with `match`: patterns are shapes

```python
match tokenize(line):
    case []:
        return Blank()
    case ["quit" | "exit" | "q"]:
        return Quit()
    case ["units", name]:
        return ListUnits(dimension_named(name))
    case ["digits", n] if n.isdecimal() and 1 <= int(n) <= MAX_DIGITS:
        return SetDigits(int(n))
    case [*source, "to" | "as" | "->", target]:
        return Convert(_quantity(source, ans), lookup(target), " ".join(source))
    case source:
        return ConvertToAll(_quantity(source, ans), " ".join(source))
```

`match` isn't a `switch` on a value. Each `case` describes a *shape*, and Python tries them top to
bottom:

- **Literals** (`"quit"`) compare with `==`.
- **Bare names** (`name`, `target`) capture whatever is in that position.
- **`*source`** captures "the rest", and it can sit anywhere, not only at the end.
- **`|`** offers alternatives inside a pattern.
- **A guard** (`if ...`) runs after the shape has matched.

So `5 ft 11 in to cm` matches the convert case, with `source=['5', 'ft', '11', 'in']` and
`target='cm'`. Notice that `in` here is a unit, not a keyword: it's just data.

`_quantity` then pairs the source up with `itertools.batched(tokens, 2, strict=True)`. That's
new in 3.13: `strict=True` raises if one token is left over, which becomes the "expected
number-unit pairs" error.

### 2. Commands as dataclasses, matched by class pattern

```python
type Command = Convert | ConvertToAll | ListUnits | ListDimensions | SetDigits | Help | Quit | Blank

match command := parse(line, ans=self.ans):
    case SetDigits(digits):
        self.digits = digits
        ...
    case Convert(quantity, target, label):
        self.ans = quantity.to(target)
        return f"{label} {describe(self.ans, self.digits)}"
    case _:
        assert_never(command)
```

`type Command = ...` is the 3.12+ alias syntax, the same idea as a TypeScript union type. A class
pattern like `Convert(quantity, target, label)` first does an `isinstance` check and then binds
the fields positionally. That works because `@dataclass` generates `__match_args__` (the field
order) for you.

`assert_never(command)` is the exhaustiveness check. mypy narrows `command` case by case, and if
you add a ninth command without handling it, `command` is no longer `Never` at that line and
mypy fails the build. That's the same trick as TypeScript's `const _: never = x`, and the same
guarantee C# gives as a warning on switch expressions.

An earlier version had one `ListUnits(dimension: Dimension | None)` and matched
`ListUnits(None)` first. mypy can't narrow a field through a pattern like that, so
exhaustiveness broke. Splitting it into `ListUnits` and `ListDimensions` made illegal states
unrepresentable, and the check passed.

### 3. Units are data: one table, one dict

```python
"km/h": (1000 / _HOUR, "kilometres-per-hour, kph, kmh"),
...
_BY_NAME: dict[str, Unit] = {spelling: u for u in UNITS for spelling in spellings(u)}
```

There's no 50-arm `switch` mapping names to factors. Each unit is a row, and a nested dict
comprehension (read the `for`s left to right, as in nested loops) builds one big
`spelling → Unit` dict. Adding a unit is one line, and lookup is a hash probe. When a name
misses, `difflib.get_close_matches` from the standard library supplies the "did you mean?".

Every unit is described by `base = value * scale + offset`. Only °C and °F need an offset, which
is why a temperature can't be just a multiplier, and why `5 C 3 C to K` is refused rather than
answered wrongly.

### 4. `Fraction` computes, `Decimal` presents

```python
_INCH = Fraction("0.0254")  # legal definition: exact
_FOOT = 12 * _INCH
_MILE = 5280 * _FOOT  # 1609.344 m, exactly


def to(self, target: Unit) -> Quantity:
    base = self.value * self.unit.scale + self.unit.offset
    return Quantity((base - target.offset) / target.scale, target)
```

`Fraction("0.0254")` is exactly 127/5000. Every conversion is a few multiplications and
divisions of rationals, so the result *is* the true answer: `98.6 F to C` is exactly 37, and
`1 km/h to m/s` is exactly 5/18. Note that `to()` returns `Quantity` without quotes. In 3.14,
annotations are evaluated lazily, so a class can name itself before its definition finishes.

Display goes through `Decimal`:

```python
with localcontext(prec=digits) as ctx:
    ctx.clear_flags()
    number = (Decimal(value.numerator) / Decimal(value.denominator)).normalize()
    exact = not ctx.flags[Inexact]
```

A `Decimal` context holds the precision, the rounding mode and a set of *signal flags*.
`localcontext` scopes a precision to this block (a `with` statement, like C#'s `using`). After
the division, `ctx.flags[Inexact]` says whether rounding discarded anything, and that flag is
the whole `=`/`≈` feature. `normalize()` strips trailing zeros, and `adjusted()` gives the power
of ten that decides between `1,609,344` and `8e+12`.

### 5. The REPL loop and its three modes

```python
if args.expression:
    return run_lines(session, [" ".join(args.expression)], sys.stdout, sys.stderr)
if sys.stdin.isatty():
    return repl(session)
return run_lines(session, sys.stdin, sys.stdout, sys.stderr)
```

`sys.stdin` is iterable line by line, so batch mode and one-shot mode share `run_lines`. One
gets a real file, the other a one-element list. In the REPL, `import readline` is imported only
for its side effect: it upgrades `input()` with arrow keys and history. `EOFError` (Ctrl-D) and
`KeyboardInterrupt` (Ctrl-C) are ordinary exceptions you catch, unlike .NET's
`Console.CancelKeyPress` event.

## If you wrote this in C# / TypeScript

| Task | C# | TypeScript | Python |
| --- | --- | --- | --- |
| Match a command shape | list patterns `[.. var src, "to", var t]` (C# 11) | no pattern matching (ts-pattern library) | `case [*src, "to", t]:` |
| Destructure a record | `Convert(var q, var t, _)` positional pattern | `if (cmd.kind === "convert")` | `case Convert(q, t, _):` |
| Exhaustiveness | switch expression warning CS8509 | `const _: never = cmd` | `assert_never(cmd)` + mypy |
| Exact decimal | `decimal` (fixed 28–29 digits) | none built in (TC39 proposal) | `Decimal` (any precision, with signals) |
| Exact rational | none built in | none built in | `fractions.Fraction` |
| Was it rounded? | compare before/after yourself | no | `ctx.flags[Inexact]` |
| Name → handler | `Dictionary<string, Unit>` | `Record<string, Unit>` / `Map` | `dict` |
| REPL line input | `Console.ReadLine()` (null on EOF) | `readline.createInterface` | `input()` (raises `EOFError`) |

The parser in each language:

```csharp
// C# 11 list patterns are genuinely close
Command Parse(string[] tokens) => tokens switch
{
    [] => new Blank(),
    ["quit" or "exit" or "q"] => new Quit(),
    ["digits", var n] when int.TryParse(n, out var d) && d is >= 1 and <= 50 => new SetDigits(d),
    [.. var source, "to" or "as" or "->", var target] => new Convert(Quantity(source), Lookup(target)),
    var source => new ConvertToAll(Quantity(source)),
};
```

```typescript
// TypeScript: no patterns, so index arithmetic and manual checks
function parse(tokens: string[]): Command {
  if (tokens.length === 0) return { kind: "blank" };
  if (tokens.length === 1 && ["quit", "exit", "q"].includes(tokens[0])) return { kind: "quit" };
  const sep = tokens.findLastIndex((t) => ["to", "as", "->"].includes(t));
  if (sep !== -1 && sep === tokens.length - 2)
    return { kind: "convert", quantity: quantity(tokens.slice(0, sep)), target: lookup(tokens[sep + 1]) };
  return { kind: "all", quantity: quantity(tokens) };
}
```

C# is the closest match here: list patterns, `or` patterns and positional record patterns map
almost one to one. Python's version is a statement, not an expression, so each arm needs a
`return`. Where Python clearly wins is the numeric tower: `Fraction` has no equivalent in either
language, and `Decimal` lets you choose the precision and inspect rounding signals, where C#'s
`decimal` is fixed-size and silent about rounding.

## Gotchas

- **A bare name in a `case` captures; it never compares.** `case MAX_DIGITS:` doesn't test
  against the constant. It matches *anything* and rebinds `MAX_DIGITS`. If it isn't the last
  case, Python refuses to compile it ("name capture makes remaining patterns unreachable"). To
  compare against a constant, use a dotted name (`case Dimension.MASS:`) or a guard.
- **Never build a `Decimal` or `Fraction` from a float.** `Decimal(0.1)` is
  `0.1000000000000000055511151231257827021181583404541015625`, and `Fraction(0.1)` is
  `3602879701896397/36028797018963968`. They faithfully preserve the float's error. Build them
  from strings or ints: `Decimal("0.1")`, `Fraction("0.1")`.
- **`->` is a redirect in your shell.** `uv run conv 5 ft 11 in -> cm` creates a file called
  `cm`. Use `to`, quote the expression, or use the REPL.

## Your turn

1. **Easy:** add an `area` dimension (`m2`, `km2`, `ha`, `ft2`, `acre`). It's a new `Dimension`
   member and one table entry. An acre is exactly 4840 square yards, so `1 acre to m2` should
   print `=`. Add it to the exact-conversions test.
2. **Medium:** support compound *targets*: `180 cm to ft in` should print `5 ft 10.866 in`.
   Match `[*source, "to", *targets]`, then peel off whole units with `divmod`, which works on
   `Fraction`. Write a parametrized test that includes `1 mi to mi ft` (`1 mi 0 ft`).
3. **Stretch:** arithmetic with derived units: `60 mi / 1.5 h to km/h`. Represent a dimension
   as exponents (`{"length": 1, "time": -1}`), parse the expression with `ast.parse(...,
   mode="eval")`, and walk only `BinOp`, `Constant` and `Name` nodes with `match`. Anything else
   is an error, never `eval`.

## Go deeper

- [PEP 636: Structural Pattern Matching tutorial](https://peps.python.org/pep-0636/)
- [`decimal`: contexts, signals and rounding](https://docs.python.org/3/library/decimal.html)
- [`fractions.Fraction`](https://docs.python.org/3/library/fractions.html)
- [`typing.assert_never`](https://docs.python.org/3/library/typing.html#typing.assert_never)
  and [`itertools.batched`](https://docs.python.org/3/library/itertools.html#itertools.batched)
- Local lessons: lesson 08 (pattern matching), lesson 07 (errors & context managers),
  lesson 05 (type hints).
