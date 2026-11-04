# Day 011 · CSV → SQLite Importer

`csv2db` loads any CSV into SQLite. It infers a real type for every column (INTEGER, REAL,
BOOLEAN, DATE, DATETIME or TEXT) and makes SQLite enforce it with `STRICT` tables and `CHECK`
constraints. Then you can run SQL over the files straight away, joins included, without writing
a database to disk. It uses nothing but the standard library.

## Run it

```bash
cd py-csv-sqlite
uv run csv2db data/messy.tsv --dry-run                  # what got inferred, and why
uv run csv2db data/customers.csv data/orders.csv        # import into memory, print the schemas
uv run csv2db data/customers.csv data/orders.csv -q "SELECT count(*) FROM orders WHERE gift"
uv run csv2db data/customers.csv data/orders.csv -o shop.db         # a real database file
uv run csv2db data/orders-november.csv -t orders -o shop.db --if-exists append
uv run python -m sqlite3 shop.db                        # Python's own SQLite shell (3.12+)
uv run pytest
```

The samples in `data/` are 40 customers (semicolon-separated, as Excel saves "CSV" in much of
Europe), 5,000 orders, a tab-separated `messy.tsv` full of inference traps, and
`orders-november.csv`, which has a deliberately broken row.

Without `-o` the database is `:memory:` and is gone when the command ends. Summaries and schemas
go to stderr and query results to stdout, so `csv2db … -q "…" > out.txt` captures just the
results.

## What it looks like

The wow moment is SQL over two CSV files, a join and an aggregate, with no setup at all:

```
$ uv run csv2db data/customers.csv data/orders.csv -q "
SELECT c.country,
       count(*) AS orders,
       round(sum(o.qty * o.unit_price * (1 - coalesce(o.discount_pct, 0) / 100)), 2) AS revenue
FROM orders o JOIN customers c ON c.id = o.customer_id
GROUP BY c.country
ORDER BY revenue DESC"
data/customers.csv → memory:customers  (40 rows, 1 ms)
data/orders.csv → memory:orders  (5,000 rows, 25 ms)
country  orders    revenue
-------  ------  ---------
FI         1148  226072.03
US         1051  197943.14
ES          770  169285.09
DE          886   164366.6
IT          787   156340.5
FR          358   77750.98
(6 rows)
```

That works because the types are real. `discount_pct` is a REAL with NULLs (so `coalesce`
works), `ordered_at` is a DATETIME that SQLite's date functions understand, and `gift` and `vip`
are 0/1 booleans that you can sum or use directly in a `WHERE`. `REGEXP` is a Python function
registered with SQLite:

```
$ uv run csv2db data/customers.csv data/orders.csv \
    -q "SELECT strftime('%Y-%m', ordered_at) AS month, count(*) AS orders, sum(gift) AS gifts
        FROM orders GROUP BY month LIMIT 3" \
    -q "SELECT name, e_mail, post_code FROM customers WHERE vip AND e_mail REGEXP '\.org$'"
…
month    orders  gifts
-------  ------  -----
2026-01     547     59
2026-02     513     57
2026-03     563     65
(3 rows)

name               e_mail                  post_code
-----------------  ----------------------  ---------
John Backus        john.5@example.org      33100
Linus Ritchie      linus.9@example.org     06000
Barbara Knuth      barbara.18@example.org  10001
Edsger Stroustrup  edsger.24@example.org   01067
Ada Lovelace       ada.40@example.org      00184
(5 rows)
```

The post codes keep their leading zeros: `00184` is TEXT, not the number 184.

`--dry-run` shows what was inferred. The "decided by" column is the value that settled each
column's type. Every row here is a trap that a naive `try: int(x)` importer falls into:

```
$ uv run csv2db data/messy.tsv --dry-run
data/messy.tsv: 3 rows
column        type                header        decided by
------------  --------  --------  ------------  ------------------
code          TEXT      not null  Code          '007'
amount        REAL      not null  Amount        '2.5'
count         TEXT      not null  Count         '1_000'
flag          BOOLEAN   not null  Flag          'true'
due           TEXT      not null  Due           '2026-02-30'
seen_at       DATETIME  not null  Seen At       '2026-11-04 09:30'
score         TEXT      not null  Score         'nan'
arabic        TEXT      not null  Arabic        '١٢٣'
notes         TEXT      3 empty   Notes
name          TEXT      not null  Name          'Ada'
name_2        TEXT      not null  name          'ada'
zazolc_gesla  TEXT      not null  Zażółć gęślą  'jaźń'

CREATE TABLE "messy" (
    "code" TEXT NOT NULL,
    "amount" REAL NOT NULL,
    "count" TEXT NOT NULL,
    "flag" INTEGER NOT NULL CHECK ("flag" IN (0, 1)),
    "due" TEXT NOT NULL,
    "seen_at" TEXT NOT NULL CHECK ("seen_at" IS NULL OR julianday("seen_at") IS NOT NULL),
    "score" TEXT NOT NULL,
    "arabic" TEXT NOT NULL,
    "notes" TEXT,
    "name" TEXT NOT NULL,
    "name_2" TEXT NOT NULL,
    "zazolc_gesla" TEXT NOT NULL
) STRICT;
```

`due` was a DATE until `2026-02-30`, which has the right shape but isn't a real day. `amount`
mixed `1` and `2.5`, so it widened to REAL. `seen_at` mixed dates and datetimes, so it widened to
DATETIME. The duplicate `Name`/`name` headers became `name` and `name_2`, and the Polish header
was folded to ASCII.

Writing a file, then appending to it. The November file has an empty `Qty` on line 3, so
SQLite refuses the row, `csv2db` names the line, and the transaction rolls back. Row 15001,
which had already gone in, is taken out again:

```
$ uv run csv2db data/customers.csv data/orders.csv -o shop.db
data/customers.csv → shop.db:customers  (40 rows, 2 ms)
column     type                  header     decided by
---------  -------  -----------  ---------  ----------------------
id         INTEGER  primary key  ID         '1'
name       TEXT     not null     Name       'Dennis Torvalds'
e_mail     TEXT     3 empty      E-mail     'dennis.1@example.org'
country    TEXT     not null     Country    'IT'
post_code  TEXT     not null     Post Code  '00184'
signed_up  DATE     not null     Signed Up  '2025-04-07'
vip        BOOLEAN  not null     VIP        'no'

data/orders.csv → shop.db:orders  (5,000 rows, 25 ms)
…
Open it with: uv run python -m sqlite3 shop.db

$ uv run csv2db data/orders-november.csv -t orders -o shop.db --if-exists append
csv2db: data/orders-november.csv, line 3: NOT NULL constraint failed: orders.qty

$ uv run python -m sqlite3 shop.db "SELECT count(*), max(ordered_at) FROM orders"
(5000, '2026-10-08 04:31:49')
```

Fill in the `Qty` (`1`) and the same command prints
`data/orders-november.csv appended to shop.db:orders  (3 rows, 1 ms)`.

The constraints protect the table from everyone, not just from `csv2db`:

```
$ uv run python -m sqlite3 shop.db "INSERT INTO customers (id, name, country, post_code, signed_up, vip)
                                     VALUES (41, 'Bob', 'PL', '00-950', '2026-02-30', 0)"
IntegrityError (SQLITE_CONSTRAINT_CHECK): CHECK constraint failed: signed_up
```

## What you'll learn

- **`sqlite3` with `autocommit=False`** (Python 3.12+), where `with conn:` is one transaction
  that covers DDL too. `DROP`, `CREATE` and 5,000 inserts commit or roll back together
  ([loader.py#L137](src/py_csv_sqlite/loader.py#L137), [db.py#L16](src/py_csv_sqlite/db.py#L16)).
- **`executemany` fed by a generator**: rows stream from the CSV straight into SQLite without
  ever all being in memory. Both passes over the file stream
  ([loader.py#L146](src/py_csv_sqlite/loader.py#L146)).
- **Type inference as a lattice**: a regex per type, `fromisoformat` to check the calendar, and a
  `frozenset`-keyed dict that makes `widen()` symmetric
  ([infer.py#L43](src/py_csv_sqlite/infer.py#L43), [infer.py#L87](src/py_csv_sqlite/infer.py#L87)).
- **SQLite `STRICT` tables plus `CHECK`** turn SQLite from "stores anything anywhere" into a
  typed database ([loader.py#L87](src/py_csv_sqlite/loader.py#L87)).
- **`create_function`** adds a Python `REGEXP` operator to SQL, and
  **`pragma_table_info(?)`** reads a table's schema with a bound parameter
  ([db.py#L10](src/py_csv_sqlite/db.py#L10), [loader.py#L114](src/py_csv_sqlite/loader.py#L114)).
- **`match` on a tuple** to decide whether new data fits an existing column
  ([infer.py#L170](src/py_csv_sqlite/infer.py#L170)).

## Code tour

### 1. Classify one cell: regexes, because `int()` is too kind

```python
# [0-9], not \d: in a str pattern \d matches every Unicode decimal digit.
_INTEGER = re.compile(r"[+-]?(?:0|[1-9][0-9]*)")  # no leading zeros: "007" is a code, not 7
_REAL = re.compile(r"[+-]?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


def classify(raw: str) -> Kind | None:
    text = raw.strip()
    if not text:
        return None
    if _INTEGER.fullmatch(text):
        return Kind.INTEGER
    if _REAL.fullmatch(text):
        return Kind.REAL
    if text.casefold() in _TRUE | _FALSE:
        return Kind.BOOLEAN
    if _DATE.fullmatch(text) and _is_valid(date, text):
        return Kind.DATE
    ...
```

The Pythonic reflex is EAFP: `try: int(s) except ValueError`. That's right for *parsing* and
wrong for *inference*, because `int()` and `float()` accept far more than a CSV author means:
`int("1_000")`, `int(" 12 ")`, `int("١٢٣")` (Arabic-Indic digits), `float("nan")`,
`float("infinity")`. `date.fromisoformat` is just as generous: since 3.11 it accepts `20261104`
and `2026-W45-3`. So the regex decides the *shape* and `fromisoformat` checks the *calendar*
(`2026-02-30` passes the regex and fails `fromisoformat`). `re.fullmatch` anchors both ends, so
you don't need `^…$`.

`Kind` is a `StrEnum`, and its `storage` property maps six logical types onto SQLite's three
storage classes with a `match … case Kind.INTEGER | Kind.BOOLEAN:`. mypy checks that the match is
exhaustive, so the property needs no fallback `return`.

### 2. Widen per column: a lattice in five lines

```python
_WIDER = {
    frozenset({Kind.INTEGER, Kind.REAL}): Kind.REAL,
    frozenset({Kind.DATE, Kind.DATETIME}): Kind.DATETIME,
}


def widen(a: Kind | None, b: Kind | None) -> Kind | None:
    if a is None or a == b:
        return b
    if b is None:
        return a
    return _WIDER.get(frozenset({a, b}), Kind.TEXT)
```

A `frozenset` is hashable, so it can be a dict key, and `{a, b} == {b, a}`. That one choice makes
the function symmetric without listing both orders. Each `Column` folds every cell through
`widen` and remembers the value that last changed its kind. That value is the "decided by"
column, which tells you *why* `due` is TEXT
([infer.py#L134](src/py_csv_sqlite/infer.py#L134)). Only a column named `id` keeps a `set` of
its values (to detect a primary key), so memory stays flat for a million-row file.

### 3. Pass 2: a generator into `executemany`, inside one transaction

```python
def load(conn: sqlite3.Connection, plan: Plan, if_exists: IfExists = "fail") -> Loaded:
    current_line = 0

    def values(kinds: list[Kind]) -> Iterator[tuple[int | float | str | None, ...]]:
        nonlocal current_line
        converters = [partial(convert, kind) for kind in kinds]
        rows = read_rows(plan.path)
        next(rows)  # the header
        for line, row in rows:
            current_line = line  # executemany pulls rows one at a time, so this is "now"
            yield tuple(conv(cell) for conv, cell in zip(converters, row, strict=True))

    with conn:
        ...
            conn.execute(f"DROP TABLE IF EXISTS {quote(plan.table)}")
            conn.execute(create_sql(plan))
        ...
        try:
            cursor = conn.executemany(
                f"INSERT INTO {quote(plan.table)} VALUES ({placeholders})", values(kinds)
            )
        except sqlite3.IntegrityError as error:
            # The generator's last row is the one SQLite just refused.
            raise ImportFailed(f"{plan.path}, line {current_line}: {error}") from error
```

There are three ideas here:

- **`executemany` takes any iterable.** It pulls a row, binds it to the prepared statement, steps,
  and repeats. The generator is lazy, so there's never a list of 5,000 tuples. The CSV is read
  a second time instead of being cached from pass 1. Rereading is cheap, and keeping the rows
  is what costs memory.
- **Laziness also gives you error locations.** SQLite's error doesn't say which row failed, but
  the generator knows which row it handed over last. `nonlocal` lets the inner function rebind
  `current_line` in `load`'s scope (it is C#'s captured variable, made explicit).
- **One transaction.** With `autocommit=False`, the `DROP`, the `CREATE` and every `INSERT` are
  in one transaction, and `with conn:` commits it or rolls it back. Committing after every row
  instead is what makes naive importers slow. Measured here on the 5,000-row file:
  `executemany` in one transaction took **4 ms**, and `execute` + `commit()` per row took
  **1,632 ms**, about 400× slower, because every commit is an fsync.

`partial(convert, kind)` pre-binds each column's kind, so the hot loop is a plain call per cell.
`zip(..., strict=True)` (Python 3.10+) raises if a row is the wrong width, instead of silently
dropping cells as plain `zip` would.

### 4. Make SQLite enforce the types

```python
def column_sql(column: Column) -> str:
    name = quote(column.name)
    kind = column.sql_kind
    parts = [name, kind.storage]
    if column.primary_key:
        parts.append("PRIMARY KEY")
    elif column.nulls == 0:
        parts.append("NOT NULL")
    match kind:
        case Kind.BOOLEAN:
            parts.append(f"CHECK ({name} IN (0, 1))")
        case Kind.DATE:
            parts.append(f"CHECK ({name} IS date({name}))")  # NULL IS NULL, so NULLs pass
        case Kind.DATETIME:
            parts.append(f"CHECK ({name} IS NULL OR julianday({name}) IS NOT NULL)")
    return " ".join(parts)
```

By default SQLite uses *type affinity*: a column declared `INTEGER` will happily store `'abc'`.
`STRICT` (SQLite 3.37+; this Python build links 3.53) allows only `INTEGER`, `REAL`, `TEXT`, `BLOB`
and `ANY`, and rejects values of the wrong type. That's why BOOLEAN and DATE need `CHECK`s on
top. `date(x)` returns NULL for a non-date and normalises a valid one, so `x IS date(x)` is true
only for canonical `YYYY-MM-DD` text. `IS` rather than `=` makes NULL pass, and `NOT NULL`
handles the NULLs where they aren't allowed.

`quote()` exists because `?` placeholders bind *values*, never identifiers. Table and column
names have to be in the SQL text, so they are cleaned up first (`to_identifier`) and then
double-quoted, with any `"` doubled. Values always go through `?`.

### 5. Python functions inside SQL

```python
def _regexp(pattern: str, value: Value) -> bool:
    # SQLite rewrites `X REGEXP Y` as regexp(Y, X): the pattern comes first.
    return value is not None and re.search(pattern, str(value)) is not None


conn = sqlite3.connect(target, autocommit=False)
conn.create_function("regexp", 2, _regexp, deterministic=True)
```

SQLite parses `REGEXP` but ships no implementation. Register a function called `regexp` and the
operator works. `deterministic=True` tells the planner that the same inputs give the same
output, so the function may be used in indexes and constant-folded. You don't need to cache
compiled patterns yourself: `re` keeps its own cache of recently compiled patterns.

## If you wrote this in C# / TypeScript

| Task | C# (.NET) | TypeScript (Node) | Python |
| --- | --- | --- | --- |
| SQLite driver | `Microsoft.Data.Sqlite` (NuGet) | `better-sqlite3` (npm), `node:sqlite` | `sqlite3`, in the stdlib |
| Transaction | `using var tx = conn.BeginTransaction(); … tx.Commit();` | `db.transaction(fn)()` | `with conn:` (with `autocommit=False`) |
| Close | `using var conn` closes it | `db.close()` | `contextlib.closing(conn)`: `with conn:` doesn't close |
| Bulk insert | reuse one `SqliteCommand`, loop, change `.Value` | `stmt.run()` in a loop inside `transaction` | `executemany(sql, iterable)` |
| Placeholders | `$name` / `@name` | `?`, `@name` | `?` (tuple) or `:name` (dict) |
| Custom SQL function | `conn.CreateFunction("regexp", …)` | `db.function("regexp", fn)` | `conn.create_function("regexp", 2, fn)` |
| Result column names | `reader.GetName(i)` | `stmt.columns()` | `cursor.description[i][0]` |
| "Is this an int?" | `int.TryParse` (also lenient: whitespace, culture) | `Number(s)` (very lenient: `""` → 0) | `int(s)` (lenient), so use a regex |
| Symmetric pair lookup | `HashSet` keys need a custom comparer | stringify the sorted pair | `frozenset({a, b})` as a dict key |

The bulk insert, side by side:

```csharp
using var tx = conn.BeginTransaction();
var cmd = conn.CreateCommand();
cmd.CommandText = "INSERT INTO orders VALUES ($id, $qty)";
var id = cmd.Parameters.Add("$id", SqliteType.Integer);
var qty = cmd.Parameters.Add("$qty", SqliteType.Integer);
foreach (var row in ReadRows(path)) { id.Value = row.Id; qty.Value = row.Qty; cmd.ExecuteNonQuery(); }
tx.Commit();
```

```python
with conn:
    conn.executemany("INSERT INTO orders VALUES (?, ?)", ((r.id, r.qty) for r in read_rows(path)))
```

Python is simpler here: the driver is in the box, and `executemany` plus a generator expression
does the prepare/bind/step loop for you. It's harder in that the transaction rules depend on how
you opened the connection (see Gotchas), and `with conn:` doesn't mean what `using` means. Also,
`sqlite3` gives you tuples, and mapping them to objects is your job. Dapper's
`Query<Order>()` has no stdlib equivalent; Day 013 uses `sqlite3.Row`.

## Gotchas

- **The default `sqlite3.connect()` can lose your table.** Without `autocommit=`, Python uses
  *legacy* transaction control: it opens a transaction implicitly before `INSERT`/`UPDATE`/
  `DELETE`, but **not** before DDL. A `DROP TABLE` + `CREATE TABLE` therefore runs in autocommit
  mode and is committed immediately. If the inserts that follow fail, the rollback can't bring
  the old table back. Tested: the same "replace then fail" leaves 0 rows with the default and
  the original 1 row with `autocommit=False`. Always pass `autocommit=False` in new code. And
  `with conn:` never closes the connection; use `contextlib.closing` or call `close()`.
- **`\d` is not `[0-9]`, and `int()` is not a validator.** In a `str` regex, `\d` matches any
  Unicode digit (`re.ASCII` or `[0-9]` fixes that), and `int()`/`float()` accept underscores,
  surrounding whitespace, non-ASCII digits, `nan` and `inf`. That's good for parsing what you
  already trust, and wrong for deciding what a column *is*.
- **SQLite's declared types are suggestions unless the table is `STRICT`.** In a normal table
  `CREATE TABLE x(n INTEGER, d DATE)` accepts `('abc', '2026-02-30')` without complaint, and
  `typeof(n)` is `'text'`. (`DATE` isn't even a SQLite type: it gets NUMERIC affinity.) Also, the
  built-in `date`/`datetime` adapters and converters are deprecated since Python 3.12. Convert to
  ISO strings yourself, as `convert()` does.

## Your turn

1. **Easy:** add `--sample N` so that pass 1 infers from only the first N data rows (inference on
   huge files gets faster). `itertools.islice(well_formed(), n)` is the whole trick. Then decide
   what should happen when row N+1 doesn't fit. The `IntegrityError` → "line N" path already
   reports it nicely; write a test that proves it.
2. **Medium:** add `--index COLUMN` (repeatable), which runs
   `CREATE INDEX "orders_customer_id" ON orders(customer_id)` inside the same transaction. Then
   add `-q "EXPLAIN QUERY PLAN SELECT …"` to the README and show the plan switching from `SCAN`
   to `SEARCH … USING INDEX`.
3. **Stretch:** make `--if-exists append` remember logical types. A STRICT table stores only
   `INTEGER`/`TEXT`, so a BOOLEAN or DATE column comes back from `pragma_table_info` as plain
   storage. Keep a `_csv2db_columns(table, column, kind)` metadata table, written in the same
   transaction as the `CREATE`. On append, convert using the stored kinds, and update `fit()` and
   its tests to match.

## Go deeper

- [`sqlite3`](https://docs.python.org/3/library/sqlite3.html), especially
  [Transaction control](https://docs.python.org/3/library/sqlite3.html#sqlite3-controlling-transactions)
  and the [`autocommit`](https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.autocommit)
  attribute
- [`Connection.create_function`](https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.create_function)
  and [`executemany`](https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.executemany)
- [`python -m sqlite3`](https://docs.python.org/3/library/sqlite3.html#command-line-interface),
  the built-in shell
- SQLite: [STRICT tables](https://sqlite.org/stricttables.html),
  [datatypes and affinity](https://sqlite.org/datatype3.html),
  [date and time functions](https://sqlite.org/lang_datefunc.html),
  [the REGEXP operator](https://sqlite.org/lang_expr.html#regexp)
- [PEP 249](https://peps.python.org/pep-0249/), the DB-API that `sqlite3`, `psycopg` and friends
  all follow
- Local lessons: lesson 13 (stdlib) and lesson 05 (type hints)
