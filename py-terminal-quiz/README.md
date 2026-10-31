# Day 008 · Terminal Quiz Game

`quiz` is a timed trivia game for your terminal. Questions come from a CSV file you can edit in
Excel. Answers are scored Kahoot-style (faster is worth more, streaks earn a bonus), typos are
forgiven, and every game prints a seed, so a friend can replay *exactly* your quiz and try to
beat your high score.

## Run it

```bash
cd py-terminal-quiz
uv run quiz                                  # 5 random questions from data/general.csv
uv run quiz --seed 2690 -n 6                 # replay a specific quiz (the demo below)
uv run quiz --daily                          # today's quiz: the same for everyone, all day
uv run quiz -c geography -d medium -n 3      # filter by category and difficulty
uv run quiz data/python.csv -n 4 --seed halloween   # Python trivia, semicolon-separated
uv run quiz --list                           # what's in the file
uv run quiz --top                            # the high-score tables
uv run quiz data/broken.csv                  # what a bad CSV looks like
uv run pytest
```

Other flags: `-t 10` sets seconds per question (default 20), `--name` the name on the board
(default: your login), `--scores PATH` the score file (default `$QUIZ_SCORES`, else
`~/.quiz-scores.json`). Blank skips a question, `:q` quits and keeps your score, Ctrl-C
abandons the game.

## What it looks like

A real game (the answers were typed into a pipe with real pauses, so the timings are real):

```text
$ uv run quiz --seed 2690 -n 6 --name Michał
general · 6 questions · 20s each · seed 2690
Replay this exact quiz: quiz --seed 2690 -n 6
Type the answer or its letter. Blank skips, :q quits.

[1/6] Computing · easy
Who created the Python programming language?
> guido van rossum
✓ Guido van Rossum  +924  (3.0s)

[2/6] Geography · easy
Which is the largest ocean on Earth?
  A) Indian    B) Atlantic    C) Pacific    D) Arctic
> c
✓ Pacific  +1,061  (1.6s, streak 2)

[3/6] Literature · easy
Which novel opens with this line?
"It was the best of times, it was the worst of times"
  A) A Tale of Two Cities    B) Oliver Twist    C) Great Expectations    D) Bleak House
> a
✓ A Tale of Two Cities  +1,095  (4.2s, streak 3)

[4/6] Science · medium
What kind of animal is a Komodo dragon?
  A) Lizard    B) Snake    C) Crocodile    D) Salamander
> c
✗ It was Lizard  (you said 'Crocodile', 3.4s)

[5/6] Geography · medium
What is the capital of Iceland?
> reykjavik
✓ Reykjavík  +1,301  (5.3s)

[6/6] History · medium
Who was the first woman to win a Nobel Prize?
> Maria Sklodowska-Curie
✓ Marie Curie, close enough to 'Maria Sklodowska-Curie'  +1,277  (8.6s)

Score 5,658 · 5/6 correct · median answer 3.8s
Fastest right answer: 1.6s, 'Pacific'
By category: Computing 1/1 · Geography 2/2 · Literature 1/1 · Science 0/1 · History 1/1

🎉 New high score for general · 6q!
🏆 general · 6q
  1. Michał         5,658  5/6   26.1s  2026-10-31  seed 2690  ← you
```

`reykjavik` matched `Reykjavík` because accents are ignored. `Sklodowska` with a plain `l` was
accepted as a typo, not an exact match; the Gotchas explain why. Ola then replays seed 2690:
same questions, same order, same A-D shuffle. She answers everything right and faster, but takes
21.4 s on the last one:

```text
[6/6] History · medium
Who was the first woman to win a Nobel Prize?
> marie curie
⏱ Right, but too slow: 21.4s (limit 20s). No points.

Score 6,650 · 5/6 correct · median answer 2.3s
...
🏆 general · 6q
  1. Ola            6,650  5/6   32.5s  2026-10-31  seed 2690  ← you
  2. Michał         5,658  5/6   26.1s  2026-10-31  seed 2690
```

[data/python.csv](data/python.csv) is semicolon-separated (what Excel exports in a Polish
locale) and has code in multi-line quoted cells. The delimiter is detected, not configured:

```text
$ uv run quiz data/python.csv -n 4 --seed halloween --name Michał
...
[2/4] Python · medium
What does this print?

    print(round(2.5), round(3.5))
  A) 2 4    B) 3 4    C) 3 3    D) 2 3
> b
✗ It was 2 4  (you said '3 4', 3.9s)
...
[4/4] Python · hard
What is [] is []?
  A) False    B) True    C) TypeError
> false
✓ False  +1,865  (4.7s, streak 2)

Score 4,068 · 3/4 correct · median answer 4.3s
```

A broken file gets every problem reported at once, with line numbers that account for
multi-line cells:

```text
$ uv run quiz data/broken.csv
quiz: data/broken.csv, line 3: difficulty 'extreme' is not one of easy, medium, hard
quiz: data/broken.csv, lines 4-5: no answer
quiz: data/broken.csv, line 6: 'water' is both right and wrong
quiz: data/broken.csv, line 7: 1 field(s) more than the header (an unquoted delimiter?)
quiz: 4 bad row(s) in data/broken.csv; fix the file and try again

$ uv run quiz --list
category        easy  medium    hard
Computing          2       2       1
Geography          2       3       1
History            1       3       1
Literature         1       1       1
Science            3       2       1
25 questions
```

The scores are plain JSON, as readable as you'd hope:

```json
{
  "version": 1,
  "boards": {
    "general · 6q": [
      {
        "name": "Ola",
        "score": 6650,
        "correct": 5,
        "total": 6,
        "seconds": 32.55,
        "seed": 2690,
        "played": "2026-10-31"
      },
```

## What you'll learn

- **The `csv` module, done properly**: `newline=""`, `utf-8-sig` for Excel's BOM, `Sniffer` to
  detect the delimiter, `DictReader`'s `restkey`, and `line_num` for error messages
  ([questions.py#L60](src/py_terminal_quiz/questions.py#L60)).
- **`ExceptionGroup` and `except*`**: collect every bad row, raise them together, and handle
  them by type ([questions.py#L83](src/py_terminal_quiz/questions.py#L83),
  [\_\_init\_\_.py#L85](src/py_terminal_quiz/__init__.py#L85)).
- **`random.Random(seed)` as a value you pass around**: reproducible quizzes, `sample` and
  `shuffle`, and str seeds for `--daily`
  ([\_\_init\_\_.py#L39](src/py_terminal_quiz/__init__.py#L39),
  [questions.py#L129](src/py_terminal_quiz/questions.py#L129)).
- **`time.perf_counter` behind an injectable clock**: a Stopwatch you can fake in tests, along
  with `input` and `print` ([game.py#L26](src/py_terminal_quiz/game.py#L26)).
- **Answer matching**: `unicodedata` NFKD to strip accents, `casefold`, and
  `difflib.SequenceMatcher` for typos ([answers.py#L29](src/py_terminal_quiz/answers.py#L29)).
- **JSON persistence without a serializer library**: `asdict` out, `Entry(**d)` back in, a
  `match` on the file's shape, and `ensure_ascii=False`
  ([scores.py#L39](src/py_terminal_quiz/scores.py#L39)).

## Code tour

### 1. Reading CSV like you mean it

```python
def load_questions(path: Path) -> list[Question]:
    # newline="" hands line endings to the csv module, which needs to see them to handle
    # newlines inside quoted fields. utf-8-sig drops the BOM that Excel puts in front.
    with path.open(newline="", encoding="utf-8-sig") as file:
        dialect = _sniff(file.read(8192))
        file.seek(0)
        reader = csv.DictReader(file, dialect=dialect, restkey=EXTRA)
        missing = [c for c in COLUMNS[:4] if c not in (reader.fieldnames or [])]
        ...
        last = reader.line_num  # line_num counts physical lines, not records
        for row in reader:
            first, last = last + 1, reader.line_num
            try:
                questions.append(_parse(row))
            except ValueError as error:
                errors.append(RowError(first, last, str(error)))
```

Every argument here prevents a real bug:

- **`newline=""`**. A text-mode file normally translates line endings before you see them. The
  csv module wants the raw characters, so it can tell a newline *inside* a quoted cell (part
  of the value) from one that ends a record. The docs make it a rule: always open CSV files
  with `newline=""`, for reading and for writing.
- **`encoding="utf-8-sig"`**. Excel's "CSV UTF-8" puts a byte-order mark first. With plain
  `utf-8` it survives decoding, and your first column is silently named `"﻿category"`.
  `-sig` strips it if present and does nothing otherwise.
- **`csv.Sniffer().sniff(sample, delimiters=",;\t")`** guesses the dialect (delimiter,
  quote character) from a sample. That's why the semicolon-separated `python.csv` needs no
  flag. It's a heuristic, so the candidates are restricted, and a failure falls back to
  `csv.excel`, the default comma dialect.
- **`DictReader`** maps each row to a dict keyed by the header. Rows with *too many* fields put
  the extras in a list under `restkey`, and rows with too few fill in `restval` (default
  `None`). Both are how `broken.csv`'s line 7 gets caught instead of silently dropping `1946`.
- **`reader.line_num`** is the number of physical lines read so far. The "Red Planet" record
  spans lines 4-5, so the row index and the line number disagree. Remembering the previous
  `line_num` gives each record's first and last line. (Reading `reader.fieldnames` is what
  consumes the header, which is why `line_num` is already 1 before the loop.)

### 2. Every error at once: `ExceptionGroup` and `except*`

Stopping at the first bad row makes a file's author fix one row per run. So `load_questions`
collects them, and raises them together (Python 3.11+):

```python
if errors:
    raise ExceptionGroup(f"{len(errors)} bad row(s) in {path}", errors)
```

The caller handles the group by the type of what's *inside* it:

```python
def _load_or_exit(path: Path) -> list[Question]:
    try:
        try:
            return load_questions(path)
        except* RowError as group:
            # `return` is a SyntaxError inside except*; raising (sys.exit raises) is allowed.
            for problem in group.exceptions:
                print(f"quiz: {path}, {problem}", file=sys.stderr)
            sys.exit(f"quiz: {group.message}; fix the file and try again")
    except OSError as error:
        sys.exit(f"quiz: can't read {path}: {error.strerror}")
```

`except* RowError` matches the `RowError`s in the group and binds `group` to a new group that
holds only those. If the group also held, say, a `KeyError`, that part would keep propagating
on its own. That's the point of `except*`: several handlers can each take *their* slice of one
group, so it isn't just `catch (AggregateException)` with an `if` inside.

Three rules show up in this one function:

- A single `try` can have `except` or `except*` clauses, but not both. Hence two `try`s.
- A plain, ungrouped exception (`FileNotFoundError`) passes through `except*` unchanged and
  reaches the outer `except OSError` as itself, not wrapped.
- `return`, `break` and `continue` are not allowed inside `except*`, because several
  `except*` clauses can run for one group and a `return` would skip the rest. Raising is fine,
  so `sys.exit(message)` does the job: it raises `SystemExit`, which prints the message to
  stderr and exits with status 1.

### 3. A random generator you can hold

```python
seed: scores.Seed = args.seed if args.seed is not None else random.randrange(10_000)
if args.daily:
    seed = date.today().isoformat()  # everyone who plays today gets the same quiz
rng = random.Random(seed)  # our own generator, not the hidden module-wide one
```

```python
chosen = rng.sample(pool, k=min(count, len(pool)))
# sorted() is stable, so questions of equal difficulty keep their random order.
return sorted(chosen, key=lambda q: q.difficulty.rank)
```

`random.randrange`, `random.choice` and friends are methods of one hidden, module-level
`Random` instance, seeded from the OS at import. Every library in the process shares it, so
calling `random.seed(42)` to get a reproducible quiz would also reseed everyone else. A
`Random(seed)` instance is private state that you pass explicitly to `pick` and `play`, which
is also what makes the tests deterministic.

Once seeded, the instance replays the same *sequence of calls* exactly: `sample` picks the
questions, then each `shuffle` (one per multiple-choice question, in `play`) orders the
options. Same seed, same calls, same quiz. That's how Ola got the same A-D letters.

A seed can be a `str` (or `bytes`) as well as an `int`; every bit of it is used, so
`--daily` seeds with `"2026-10-31"` and `--seed halloween` just works. This is the `random`
module, which is fine for games and simulations. Day 3's `secrets` is for anything an attacker
might want to predict.

### 4. A Stopwatch you can fake

```python
def play(
    questions: Sequence[Question],
    rng: random.Random,
    *,
    limit: float,
    ask: Callable[[str], str] = input,
    say: Callable[[str], object] = print,
    clock: Callable[[], float] = time.perf_counter,
) -> list[Answer]:
    ...
        start = clock()  # perf_counter: monotonic and high-resolution, i.e. a Stopwatch
        try:
            reply = ask("> ")
        except EOFError:
            say("")
            break
        seconds = clock() - start
```

`time.perf_counter()` returns float seconds from an arbitrary starting point. Only
differences mean anything. It's monotonic (it never goes backwards) and it's the
highest-resolution clock available. That makes it `Stopwatch.GetTimestamp()` and
`performance.now()`. `time.time()` is wall-clock time, which NTP or a user can change in the
middle of a question, and that's not what you want for measuring durations.

The dependencies are just default arguments holding functions: `input`, `print` and
`perf_counter` are ordinary objects. Production code calls `play(chosen, rng, limit=20)`, and
the tests pass a scripted `ask` that raises `EOFError` when it runs out (as real `input()`
does on Ctrl-D) and a fake clock. No `IClock` interface, no DI container, no mocking library:

```python
def fake_clock(*durations: float) -> Callable[[], float]:
    def ticks() -> Iterator[float]:
        now = 0.0
        for d in durations:
            yield now
            now += d
            yield now

    return ticks().__next__
```

A bound `__next__` of a generator is a zero-argument callable that returns the next value:
exactly the shape of `perf_counter`.

### 5. Forgiving answers

```python
def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    bare = "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()
    bare = re.sub(r"(?<=\w)-(?=\w)", " ", bare)  # "comma-separated", but keep the sign of "-4"
    return " ".join(re.findall(r"[\w.+-]+", bare))
```

NFKD decomposition turns `í` into `i` followed by a combining acute accent (U+0301), and
`unicodedata.combining()` identifies the accent so you can drop it. `casefold()` is
`lower()` for comparisons: `"Straße".casefold() == "strasse"`, which `lower()` doesn't give
you. That's roughly `string.Compare(a, b, CultureInfo.InvariantCulture,
CompareOptions.IgnoreNonSpace | CompareOptions.IgnoreCase)` built by hand. Python has no
culture-aware comparer in the standard library.

Typos go through `difflib.SequenceMatcher(None, given, answer).ratio()` (2 × matching
characters / total characters), but only for free-text answers that contain letters. `1988`
is not close enough to `1989`, and on a multiple-choice question a near miss is just a wrong
pick.

## If you wrote this in C# / TypeScript

| Task | C# | TypeScript (Node) | Python |
| --- | --- | --- | --- |
| Parse CSV | CsvHelper (NuGet), or `TextFieldParser` | `csv-parse` (npm) | `csv.DictReader`, in the stdlib |
| Guess the delimiter | CsvHelper `DetectDelimiter` | `papaparse` auto-detect | `csv.Sniffer().sniff()` |
| Seeded RNG | `new Random(42)` | none built in (`seedrandom`) | `random.Random(42)`, or a str seed |
| Pick k distinct items | shuffle, then `Take(k)` (`GetItems` repeats) | shuffle, then `slice` | `rng.sample(pool, k)` |
| Measure elapsed time | `Stopwatch.StartNew()`, `.Elapsed` | `performance.now()` | `time.perf_counter()` differences |
| Several errors as one | `AggregateException`, `catch` + inspect | `AggregateError` | `ExceptionGroup`, `except*` per type |
| Mockable clock | `TimeProvider` (.NET 8+) | inject a `() => number` | a `clock=time.perf_counter` parameter |
| Object ↔ JSON | `JsonSerializer.Serialize(entry)` | `JSON.stringify(entry)` | `json.dumps(asdict(entry))`, `Entry(**d)` |

Measuring one answer, side by side:

```csharp
var sw = Stopwatch.StartNew();
var reply = Console.ReadLine();          // null on Ctrl-D/Ctrl-Z
var seconds = sw.Elapsed.TotalSeconds;
```

```python
start = time.perf_counter()
reply = input("> ")  # raises EOFError on Ctrl-D
seconds = time.perf_counter() - start
```

The CSV story is where Python is plainly ahead: a correct, quoting-aware reader and writer
ships with the language, while .NET and Node send you to a package. C# is ahead on the clock:
`TimeProvider` is a standard abstraction that every library agrees on, whereas Python relies
on each function exposing its own `clock=` parameter (or on monkeypatching `time.perf_counter`
in tests). And `except*` has no real equivalent in C#/TS. The closest is unpacking
`AggregateException.InnerExceptions` by hand.

## Gotchas

- **A `StrEnum` sorts as strings.** `sorted(Difficulty)` is `[EASY, HARD, MEDIUM]`, because
  `"hard" < "medium"` alphabetically. A `StrEnum` member *is* a `str`, comparisons included.
  `pick` sorts on `difficulty.rank` (definition order) instead, and a test pins the trap down.
  An `IntEnum` would sort correctly but wouldn't parse straight from the CSV's text.
- **NFKD strips accents, not letters.** `í`, `é` and `ü` decompose into a base letter plus a
  combining mark. Polish `ł`, Danish `ø` and German `ß` don't decompose at all: they're
  separate letters. So `Sklodowska` doesn't normalise to `Skłodowska`, and only the typo check
  saved that answer. To fold those letters, you need an explicit table
  (`str.maketrans("łø", "lo")`) or a library such as `unidecode`.
- **`input()` can't time out.** The 20 s limit is enforced *after* you answer, and a late answer
  scores 0. A real countdown would need `select` on stdin (POSIX only), `signal.alarm` (POSIX
  only, main thread only), or a reader thread, and a blocked thread can't be cancelled.
  That's a job for asyncio (`asyncio.timeout`, later in this series) or a TUI framework.

One more thing: `random.Random(seed)` guarantees the same `random()` floats across Python
versions, but the docs make no such promise for `sample` or `shuffle`. A seed shared between
3.14 and some future 3.x might produce a different quiz.

## Your turn

1. **Easy:** add a `--review` flag. After the summary, list only the questions you got wrong,
   skipped or answered too slowly, with the right answer and every accepted alternative
   (`" / ".join(q.answers)`). Keep it a function, `review(answers) -> str`, and test it with the
   `scripted`/`fake_clock` helpers from `tests/test_game.py`.
2. **Medium:** `quiz --export out.csv` writes the current selection (after `-c`/`-d`/`-n`) back
   out as CSV with `csv.DictWriter`, choosing the delimiter with `--delimiter ';'`. Write a
   round-trip test: export to `tmp_path`, load it with `load_questions`, and assert the
   questions are equal, including the multi-line Dickens question. You'll discover why
   `DictWriter` needs `newline=""` too.
3. **Stretch:** a real countdown on POSIX. Replace `ask` with a function that uses
   `select.select([sys.stdin], [], [], remaining)` in a loop, redraws `⏳ 14s` on the prompt
   line with `\r` once a second, and returns `None` when time runs out, which `play` treats as
   too slow. It plugs in through the existing `ask=` parameter, so `play` needs only to handle
   `None`. Test it with `os.pipe()` as a fake stdin, and keep the current `input` path for
   Windows (`sys.platform == "win32"`).

## Go deeper

- [`csv`](https://docs.python.org/3/library/csv.html), especially the footnote on `newline=""`,
  plus [`Sniffer`](https://docs.python.org/3/library/csv.html#csv.Sniffer) and
  [`DictReader`](https://docs.python.org/3/library/csv.html#csv.DictReader)
- [`random`](https://docs.python.org/3/library/random.html), and its section on
  [reproducibility](https://docs.python.org/3/library/random.html#notes-on-reproducibility)
- [`time.perf_counter`](https://docs.python.org/3/library/time.html#time.perf_counter) and
  [PEP 418](https://peps.python.org/pep-0418/), on why Python has several clocks
- [Exception groups and `except*`](https://docs.python.org/3/tutorial/errors.html#raising-and-handling-multiple-unrelated-exceptions),
  and [PEP 654](https://peps.python.org/pep-0654/) for the design
- [`unicodedata.normalize`](https://docs.python.org/3/library/unicodedata.html#unicodedata.normalize),
  [`str.casefold`](https://docs.python.org/3/library/stdtypes.html#str.casefold) and
  [`difflib.SequenceMatcher`](https://docs.python.org/3/library/difflib.html#difflib.SequenceMatcher)
- [`json`](https://docs.python.org/3/library/json.html) and
  [`dataclasses.asdict`](https://docs.python.org/3/library/dataclasses.html#dataclasses.asdict)
- Local lessons: lesson 07 (errors and context managers), lesson 12 (testing), lesson 13
  (stdlib and ecosystem).
