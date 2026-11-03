# Day 010 · Habit Tracker with Streaks

`habit` logs habits to a plain-text file and works out streaks for any schedule: daily,
weekdays, `mon,wed,fri`, or "3 times a week". It shows them as a status table, a month
calendar or a GitHub-style heatmap, in 24-bit colour, all with nothing but the standard
library.

## Run it

```bash
cd py-habit-tracker
uv run habit -f data/habits.log --today 2026-11-03               # the status table
uv run habit -f data/habits.log --today 2026-11-03 year          # 26-week heatmap (-w 52 for a year)
uv run habit -f data/habits.log --today 2026-11-03 cal run 2026-09
uv run habit -f data/habits.log --today 2026-11-03 cal gym 2026-10
uv run habit -f data/habits.log --today 2026-11-03 cal piano --sunday
uv run pytest
```

`data/habits.log` holds six months of made-up check-ins for four habits. `--today` pins the date
so the output matches what's below. Drop it and the tool uses your local `date.today()`.

For real use, leave out `-f`. The log then lives in `$HABITS_FILE`, else `~/.habits.log`:

```bash
uv run habit add run                          # --every daily is the default
uv run habit add gym --every "3x week"        # also: weekdays, weekends, mon,wed,fri, 2/week
uv run habit done run                         # today
uv run habit done gym yesterday -3 fri        # several days at once; weekday = most recent one
uv run habit undo gym fri
uv run habit                                  # same as `habit status`
```

Colour is on when stdout is a terminal. Piping turns it off, and so do `NO_COLOR=1` and
`--color never`. `--color always` forces it on, for example for `less -R`.

## What it looks like

The status table. `!` means the streak is alive but needs today (or this week) to keep going:

```
$ uv run habit -f data/habits.log --today 2026-11-03
habit  schedule     now  streak     best     last 14 days
                                             WTFSSMTWTFSSMT
run    daily        due  23 days !  42 days  ●●●●●●●●●●●●●·
read   weekdays     ✓    12 days    30 days  ●●●  ●●●●●  ●●
gym    3/week       1/3  6 weeks !  8 weeks   ●● ● ●●  ●●●
piano  mon,wed,fri  -    20 days    20 days  ● ●  ● ● ●  ●

● done  · missed  ! keep the streak alive: due today / this week
```

`read` skips weekends in its strip and its streak still runs through them. `piano` isn't due on
a Tuesday, so its "now" column is `-`. In a terminal `●` is green, a missed `·` is red, the at-risk
streaks are yellow, and a live personal best is bold green.

Checking in moves things (on a copy of the sample, with the same `--today`):

```
$ uv run habit done run
run Tue 03 Nov: recorded
Streak: 24 days (best 42 days)
$ uv run habit done gym today -2 -3
gym Sat 31 Oct: no change
gym Sun 01 Nov: no change
gym Tue 03 Nov: recorded
Streak: 6 weeks (best 8 weeks)
```

The heatmap. Weeks run left to right, Monday at the top, and the shade is the share of habits
done that day. In colour it is GitHub's five greens; the glyphs keep it readable without
colour:

```
$ uv run habit year
     May   Jun     Jul     Aug       Sep     Oct     Nov
Mon  ▒ ▢ ▓ ░ ▒ ▓ ▓ ▓ ▓ ▒ ▓ ▓ ▓ ▓ █ █ ▒ ▓ ▓ ▒ █ ▒ ▒ ▓ ▓ █
     ▒ ▒ ▒ ▒ ▓ ▓ ▓ ░ ▒ ▒ ▒ ▓ ▓ ▓ ▒ ▒ ▓ ▓ ▒ ░ ▓ ▓ ▓ ▒ ▓ ░
Wed  ▒ ▒ ▒ ▓ ▓ ▓ ▓ ▒ ▓ ▒ ░ ▒ █ ▓ ▒ ▓ ░ ░ ░ ▓ ▓ ▓ ▓ ▓ █
     ▒ ▒ ▓ ▒ ▒ ▓ ▒ ▒ ▒ ▓ ░ ░ ▒ ▓ ░ ░ ░ ▒ ░ ▒ ▓ ▓ ▓ ▓ ▒
Fri  ▓ ▓ ▒ ▒ ▒ ▒ ▓ ▓ ▓ ▒ ▒ ▓ ▒ ▓ ▒ ▒ ▓ ▒ ▓ ▒ ▓ ▓ ▓ █ ▓
     ░ ▒ ▒ ░ ▒ ░ ░ ░ ░ ▒ ▒ ░ ░ ░ ░ ▒ ░ ▢ ░ ▒ ▢ ▢ ░ ░ ▒
Sun  ░ ▒ ░ ▒ ░ ░ ░ ░ ░ ▢ ▢ ░ ▒ ▒ ▒ ▒ ░ ░ ░ ▢ ░ ▒ ░ ▒ ▒

371 check-ins in 26 weeks (4 habits)    less ▢ ░ ▒ ▓ █ more
```

Month calendars come from the `calendar` module. September was a bad month for running, and the
red dots show it:

```
$ uv run habit cal run 2026-09
      September 2026          run · daily
 Mo  Tu  We  Th  Fr  Sa  Su
     1●  2·  3·  4●  5●  6·
 7·  8●  9· 10● 11· 12· 13●
14● 15· 16· 17· 18· 19● 20●
21· 22· 23· 24● 25● 26● 27·
28● 29● 30●
```

A weekly habit gets a score at the end of each row instead. The first row says 3/3 because that
week (28 Sep – 4 Oct) mostly falls in September:

```
$ uv run habit cal gym 2026-10
       October 2026           gym · 3/week
 Mo  Tu  We  Th  Fr  Sa  Su
             1●  2   3   4    3/3
 5   6●  7   8●  9  10  11●   3/3
12  13● 14  15● 16● 17  18    3/3
19  20  21  22● 23● 24  25●   3/3
26  27● 28● 29  30  31●       4/3
```

`--sunday` starts the week on Sunday (`calendar.Calendar(firstweekday=calendar.SUNDAY)`):

```
$ uv run habit cal piano --sunday
       November 2026          piano · mon,wed,fri
 Su  Mo  Tu  We  Th  Fr  Sa
 1   2●  3   4   5   6   7
 8   9  10  11  12  13  14
…
```

The log is plain text, so `grep`, `git diff` and your editor all work on it:

```
$ head -9 data/habits.log
# Sample habit log for Day 010. Lines are `habit NAME SCHEDULE SINCE` or `YYYY-MM-DD NAME`.
# Edit it by hand if you like: blank lines and # comments are ignored.
habit run    daily        2026-05-04
habit read   weekdays     2026-05-04
habit gym    3/week       2026-05-04
habit piano  mon,wed,fri  2026-08-03

2026-05-04 read
2026-05-04 run
```

## What you'll learn

- **`date` arithmetic with `timedelta`, and `toordinal()`**, which turns dates into plain
  integers. Week number and weekday become one `divmod`
  ([schedule.py#L19](src/py_habit_tracker/schedule.py#L19)).
- **`itertools.groupby` runs**: the value-minus-index trick finds consecutive streaks in one
  pass ([streaks.py#L29](src/py_habit_tracker/streaks.py#L29)).
- **The `calendar` module**: `Calendar(firstweekday=…).monthdatescalendar()` hands you whole
  weeks of real `date`s, plus `month_name` and `month_abbr`
  ([render.py#L102](src/py_habit_tracker/render.py#L102)).
- **ANSI colour done properly**: 24-bit SGR escapes, the `NO_COLOR` convention plus `isatty()`,
  and padding by *visible* width ([render.py#L29](src/py_habit_tracker/render.py#L29)).
- **`match` on `str.split()`** as a tiny line parser, with a guard per line shape
  ([log.py#L66](src/py_habit_tracker/log.py#L66)).
- **A union of two dataclasses** (`type Schedule = OnDays | PerWeek`) that share an interface
  by convention, with `match` on class patterns to turn them back into text
  ([schedule.py#L99](src/py_habit_tracker/schedule.py#L99)).

## Code tour

### 1. Dates as integers: `toordinal()` and `divmod`

The hard part of streaks is "consecutive". For a daily habit it means consecutive days. For
`mon,wed,fri` it means Mon → Wed → Fri → *next* Mon. For `3/week` it means consecutive weeks,
including the week that spans New Year. The trick is to number every schedule's periods so
that consecutive simply means `n, n + 1`:

```python
def week_and_day(d: date) -> tuple[int, int]:
    return divmod(d.toordinal() - 1, 7)


@dataclass(frozen=True, slots=True)
class OnDays:
    weekdays: frozenset[int]

    unit = "day"
    need = 1

    def period(self, d: date) -> int | None:
        week, weekday = week_and_day(d)
        if weekday not in self.weekdays:
            return None
        order = sorted(self.weekdays)
        return week * len(order) + order.index(weekday)
```

- **Days as integers.** `date.toordinal()` counts days from 0001-01-01. That date was a Monday,
  so `divmod(ordinal - 1, 7)` gives `(weeks since then, weekday)`, and the weekday matches
  `date.weekday()` (Monday = 0). One integer division replaces all the calendar maths, with no
  year boundaries and no ISO week numbers. `DateOnly.DayNumber` in .NET is the same idea.
- **`mon,wed,fri`** has 3 slots per week, so week 5's Wednesday is period `5 * 3 + 1`. A
  Saturday isn't in the schedule, gets `None`, and is simply skipped. That's why a weekend
  never breaks a weekdays streak.
- **`PerWeek.period` is just the week number.** Both classes expose `period`, `latest`,
  `need` and `unit`, so `streak()` never asks which schedule it has. That's duck typing; Day 23
  formalises it with `Protocol`.
- **Class attributes inside a dataclass.** `unit = "day"` has no annotation, so it isn't a
  field. It's a plain class attribute. Add `: str` and it would become a constructor
  parameter.

### 2. Streaks with `groupby`: value minus index

```python
def runs(periods: Iterable[int]) -> list[range]:
    found = []
    for _, group in groupby(enumerate(periods), key=lambda pair: pair[1] - pair[0]):
        members = [period for _, period in group]
        found.append(range(members[0], members[-1] + 1))
    return found
```

- **The trick.** For `[3, 4, 5, 9, 10]`, `enumerate` pairs give `(0, 3) (1, 4) (2, 5) (3, 9)
  (4, 10)`. Value minus index is `3, 3, 3, 6, 6`. A consecutive run keeps the same difference,
  and `groupby` groups *adjacent* equal keys, so each group is one streak.
- **`range` as the run's type.** `len(r)` is the streak length and `r[-1]` its last period. It
  takes O(1) memory and compares by value in tests (`range(3, 6) == range(3, 6)`).
- **`groupby` isn't SQL's `GROUP BY` or LINQ's `GroupBy`.** It only merges neighbours. That's
  exactly right here, and it's a classic trap elsewhere (see Gotchas).

`streak()` then has one rule to apply. The last run is "current" if it ends at the latest due
period, or at the one before it while today's period is still open:

```python
now = schedule.latest(today)  # the period that ends a live streak
still_open = schedule.period(today) == now  # today is part of it, so it isn't over yet
if found and found[-1][-1] == now:
    current = len(found[-1])
elif found and found[-1][-1] == now - 1 and still_open:
    current, at_risk = len(found[-1]), True
```

### 3. The `calendar` module does the grid

```python
cal = calendar.Calendar(firstweekday=calendar.SUNDAY if sunday else calendar.MONDAY)
header = " ".join(f"{DAY_NAMES[d][:2].title():>3}" for d in cal.iterweekdays())
for week in cal.monthdatescalendar(year, month):  # whole weeks, padded with other months
    for d in week:
        if d.month != month:
            ...
```

- **No grid maths.** `monthdatescalendar` returns a list of weeks, each a list of 7 real `date`
  objects, padded with the neighbouring months' days. You never have to work out "which
  weekday is the 1st".
- **Flipping to a Sunday start** only takes `firstweekday`. `iterweekdays()` gives the header
  order to match.
- **Also in the module:** `calendar.month_name[10]` is `"October"` (index 0 is `""`, so months
  are 1-based like `date.month`), `calendar.month_abbr` labels the heatmap, and
  `calendar.monthrange(2026, 2)` gives `(weekday of the 1st, days in month)`. `python -m
  calendar 2026` prints a whole year.
- **Locale.** These names follow the process locale (`locale.setlocale`). They are English
  here because Python starts in the C locale. That's why the parsers use a fixed
  `DAY_NAMES` tuple, not `calendar.day_abbr`.

### 4. ANSI colour: render in colour, strip at the edge

```python
def paint(text: str, rgb: RGB | None = None, *, bold: bool = False, under: bool = False) -> str:
    codes = [*(["1"] if bold else []), *(["4"] if under else [])]
    if rgb:
        codes.append("38;2;{};{};{}".format(*rgb))
    return f"\x1b[{';'.join(codes)}m{text}\x1b[0m" if codes else text


def wants_colour(mode: str, stream: TextIO) -> bool:
    match mode:
        case "always":
            return True
        case "never":
            return False
        case _:
            return not os.environ.get("NO_COLOR") and stream.isatty()
```

- **SGR codes.** `ESC[38;2;R;G;Bm` sets a 24-bit foreground colour, `1` is bold, `4` is
  underline, and `ESC[0m` resets. Any modern terminal (macOS Terminal, iTerm2, Windows Terminal,
  VS Code) understands them. You don't need a library like `colorama` any more.
- **One render path.** Everything renders in colour, and `main()` prints
  `plain(out)` (a one-regex strip) when colour is off. Every glyph already carries the
  meaning (`●`, `·`, `▢░▒▓█`), so nothing is lost without colour, and there is only one code
  path to test.
- **The convention.** Honour [no-color.org](https://no-color.org) and only colour a TTY, so
  `habit | grep run` gets clean text.
- **Padding.** A coloured `✓` is 22 characters long but one column wide. That's why
  `status_table` pads with `pad()`, which measures `len(plain(text))`, instead of `f"{s:<5}"`.

### 5. A line parser in one `match`

```python
match line.split():
    case []:
        pass
    case ["habit", name, schedule, since] if NAME.fullmatch(name):
        log.habits[name.lower()] = Habit(
            name.lower(), parse_schedule(schedule), date.fromisoformat(since)
        )
    case ["habit", *_]:
        raise ValueError("expected `habit NAME SCHEDULE SINCE`, e.g. `habit run daily 2026-06-01`")
    case [day, name] if name.lower() in log.habits:
        log.done[name.lower()].add(date.fromisoformat(day))
    case [_, name]:
        raise ValueError(f"check-in for {name!r} before a `habit {name} …` line declares it")
    case _:
        raise ValueError("expected `habit NAME SCHEDULE SINCE` or `YYYY-MM-DD NAME`")
```

- **Whole-shape matching.** A sequence pattern matches the list's *length and contents* in one
  go and binds the parts. Order matters: the specific `"habit"` cases come before the generic
  2-word one.
- **Error reporting.** `load()` catches every `ValueError` (including `date.fromisoformat`'s
  own) and re-raises it as `LogError("habits.log:3: …")`, so a hand-edited typo points at its
  line.
- **Writes.** `done` appends with mode `"a"` (O_APPEND), so a check-in never rewrites the file.
  Only `undo` does, using Day 4's temp-file + `os.replace` recipe.

## If you wrote this in C# / TypeScript

| Task | C# | TypeScript | Python |
| --- | --- | --- | --- |
| A date with no time | `DateOnly` (.NET 6+) | none (`Date` is always a timestamp; Temporal's `PlainDate`) | `datetime.date` |
| Add days | `d.AddDays(3)` | `new Date(d.getTime() + 3 * 864e5)` (DST bugs!) | `d + timedelta(days=3)` |
| Days between | `d2.DayNumber - d1.DayNumber` | `Math.round((b - a) / 864e5)` | `(d2 - d1).days` |
| Day of week | `DayOfWeek` (Sunday = 0) | `getDay()` (Sunday = 0) | `weekday()` (Monday = 0), `isoweekday()` (Monday = 1) |
| Month numbering | 1-12 | `getMonth()` is **0-11** | 1-12 |
| ISO week | `ISOWeek.GetWeekOfYear` | none built in | `d.isocalendar().week` |
| Month grid | none; compute it | none; compute it | `calendar.Calendar().monthdatescalendar(y, m)` |
| Parse `2026-11-03` | `DateOnly.ParseExact(s, "yyyy-MM-dd")` | `new Date(s)` (UTC midnight!) | `date.fromisoformat(s)` |
| Colour output | `Console.ForegroundColor` (16 colours) | chalk / picocolors | raw `\x1b[38;2;…m` + `NO_COLOR` |

The same "yesterday" in each:

```ts
const d = new Date();               // a timestamp, not a date
d.setDate(d.getDate() - 1);         // mutates; right across DST only because setDate is local
const iso = d.toISOString().slice(0, 10);   // UTC! Just after midnight in Warsaw: 2 days ago
```

```python
yesterday = date.today() - timedelta(days=1)  # an immutable value, local, no time component
str(yesterday)  # '2026-11-02', always ISO 8601
```

Python's `date` is what JavaScript has been missing since 1995: immutable, timezone-free, with
arithmetic that can't be off by an hour. C#'s `DateOnly` is just as good, and arguably clearer
because it's a separate type rather than a parent class of `datetime` (see Gotchas). Where
Python wins outright is the batteries: `calendar`, `isocalendar()` and `fromisoformat` are all
built in. C# is better at console colour on old Windows consoles. On anything modern, ANSI
works everywhere.

## Gotchas

- **`datetime` is a subclass of `date`.** `isinstance(datetime.now(), date)` is `True`, so a
  `date` parameter happily accepts a `datetime`. Then `date(2026, 1, 1) < datetime(2026, 1, 1)`
  raises `TypeError`, and `==` between them is just `False`. Keep days as `date`: call
  `.date()` on any `datetime` at the boundary. The `set[date]` here would silently never match
  a `datetime`.
- **`date.today()` is local time, and `--today` exists for a reason.** A habit day is your day,
  so local is right. But a function that calls `date.today()` inside can't be tested at 23:59 or
  across a week boundary, so every function here takes `today` as a parameter. Separately,
  `isocalendar()` puts 2026-12-29 and 2027-01-02 in *2026*-W53. That's why `PerWeek` numbers
  weeks from `toordinal()` instead of using `(year, week)` tuples.
- **`groupby` only groups neighbours.** `groupby("aabaa")` gives `a, b, a`, three groups. The
  value-minus-index trick depends on that, but if you wanted SQL-style grouping you must
  `sorted(…, key=k)` by the same key first.

## Your turn

1. **Easy: Completion rate.** Add a `rate` column to the status table: the share of due periods
   met in the last 30 days, e.g. `87%`. You have the pieces: `counts(habit, days)`,
   `schedule.period(d)` for the days in `range(30)`, and `schedule.need`. Decide what a
   half-done week counts as.
2. **Medium: Freeze days.** Add a `habit skip NAME DAY` command that writes `2026-11-05 run
   skip`. A skipped period should neither break nor extend a streak, like a weekend for a
   weekdays habit. You'll need a third `case` in the parser and a way for `streak()` to treat
   skipped periods as "not scheduled".
3. **Stretch: Year in review.** Make `habit year --calendar 2026` print a whole year as twelve
   small month grids, three per row, like `python -m calendar 2026` but coloured per day by the
   heatmap level. `calendar.Calendar.yeardatescalendar(2026, width=3)` gives you the layout.
   The hard part is zipping three months' rows side by side when they have different numbers
   of weeks (`itertools.zip_longest`).

## Go deeper

- [`datetime.date`](https://docs.python.org/3/library/datetime.html#date-objects), including
  [`toordinal`](https://docs.python.org/3/library/datetime.html#datetime.date.toordinal) and
  [`isocalendar`](https://docs.python.org/3/library/datetime.html#datetime.date.isocalendar)
- [`calendar`](https://docs.python.org/3/library/calendar.html), in particular
  `Calendar.monthdatescalendar`
- [`itertools.groupby`](https://docs.python.org/3/library/itertools.html#itertools.groupby)
- [ANSI escape codes (SGR)](https://en.wikipedia.org/wiki/ANSI_escape_code#SGR) and
  [no-color.org](https://no-color.org)
- [Structural pattern matching tutorial (PEP 636)](https://peps.python.org/pep-0636/)
- Local lessons: lesson 13, stdlib and ecosystem (`datetime`, `calendar`), lesson 06,
  iterators and generators (`itertools`), and lesson 08, pattern matching.
