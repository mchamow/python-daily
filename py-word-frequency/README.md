# Day 001 · Word Frequency Counter

`wordfreq` finds the most frequent words across a pile of text files, and the words that make
each file *different* from the others.

## Run it

```bash
cd py-word-frequency
uv run wordfreq data/                              # top 10 words across three novels
uv run wordfreq data/ --ignore said --ignore one   # add your own stop words
uv run wordfreq data/ --distinctive -n 5           # what makes each book different
head -c 2000 data/moby-dick.txt | uv run wordfreq - --json -n 3   # stdin in, JSON out
uv run wordfreq --help
uv run pytest
```

`data/` holds public-domain excerpts from *Alice in Wonderland*, *Pride and Prejudice* and
*Moby-Dick* (see [data/SOURCES.md](data/SOURCES.md)). `uv run wordfreq` works because
`pyproject.toml` declares a console script: `wordfreq = "py_word_frequency:main"`.

## What it looks like

```text
$ uv run wordfreq data/ --ignore said --ignore one
Scanned 3 files · 20,028 words · 8,910 counted · 3,346 distinct

   1  alice        74  ████████████████████████████████
   2  little       70  ██████████████████████████████
   3  like         55  ████████████████████████
   4  thought      46  ████████████████████
   5  see          43  ███████████████████
   ...
```

The standout is `--distinctive`. Plain frequency says all three books are about "little" and
"thought". Comparing each book with the other two finds the words that belong to it:

```text
$ uv run wordfreq data/ --distinctive -n 5
data/alice-in-wonderland.txt
  alice    122.1×  (74 times)
  mouse     66.7×  (40 times)
  dodo      22.8×  (13 times)
  rabbit    21.2×  (12 times)
  cats      19.5×  (11 times)

data/moby-dick.txt
  harpooneer    33.1×  (32 times)
  landlord      28.1×  (27 times)
  ...

data/pride-and-prejudice.txt
  bingley    76.3×  (37 times)
  bennet     60.3×  (29 times)
  ...
```

Errors go to stderr and the exit code is 2, so the tool behaves well in shell scripts:

```text
$ uv run wordfreq data/nope.txt; echo "exit=$?"
wordfreq: data/nope.txt: no such file or directory
exit=2
```

## What you'll learn

- **`collections.Counter`**: a dict subclass that counts things and supports `+` and `-`
  between counters ([analysis.py#L43](src/py_word_frequency/analysis.py#L43)).
- **Generators as streams.** `words()` yields one word at a time, and `Counter` consumes the
  stream without building a list ([text.py#L31](src/py_word_frequency/text.py#L31)).
- **`argparse`**: positional `nargs="+"`, repeatable flags and mutually exclusive options from
  the standard library ([\_\_init\_\_.py#L14](src/py_word_frequency/__init__.py#L14)).
- **`pathlib`**: recursive globbing, and reading files that might hold bad bytes
  ([sources.py#L35](src/py_word_frequency/sources.py#L35)).
- **Unicode-correct text handling**: `casefold()`, `\N{...}` escapes and a letters-only regex
  ([text.py#L10](src/py_word_frequency/text.py#L10)).
- **Package data with `importlib.resources`**: the stop-word list ships inside the package
  ([text.py#L26](src/py_word_frequency/text.py#L26)).

## Code tour

### 1. Tokenising: a regex plus a generator

```python
_WORD = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)*")


def words(text: str) -> Iterator[str]:
    for match in _WORD.finditer(text.translate(_APOSTROPHES)):
        yield match.group().casefold()
```

The standard `re` module has no `\p{L}` (the third-party `regex` package does). `[^\W\d_]`
reads as "a word character that isn't a digit or underscore", which in Python 3 means *any
Unicode letter*, so `café` and `Straße` work. The non-capturing group keeps `don't` and
`o'clock` as single words.

Because `words` contains `yield`, calling it returns a generator and runs nothing yet. That's
C#'s `yield return`. `finditer` is lazy as well, so the whole pipeline processes one match at a
time.

`casefold()` is the Unicode-aware version of `lower()`: `"Straße".casefold() == "strasse"`.
C#'s `ToLowerInvariant()` leaves `ß` alone.

### 2. Counting is one call

```python
def count_words(words: Iterable[str]) -> Counter[str]:
    return Counter(words)
```

`Counter` is a `dict[str, int]` that builds itself from any iterable. Today it consumes the
generator above. `counter.most_common(10)` sorts, `counter.total()` sums, and a missing key
returns `0` instead of raising `KeyError`. Filtering happens on the *vocabulary* (about 3,300
distinct words) rather than the token stream (20,000 words), using a dict comprehension inside
`filter_counts`.

### 3. Counter algebra: the distinctive-words score

```python
total: Counter[str] = sum(per_doc.values(), Counter())  # merge all documents
for name, counts in per_doc.items():
    rest = total - counts  # everything *except* this one
    ...
    result[name] = heapq.nlargest(top, scored, key=attrgetter("lift"))
```

Counters support arithmetic. `a + b` adds counts word by word, and `a - b` subtracts them,
dropping words that reach zero. So "every other book" is literally `total - counts`. `sum()`
works because it just applies `+` repeatedly; you pass `Counter()` as the start value, because
the default start is `0`.

The score itself is the ratio of a word's rate in this book to its rate in the others. Adding 1
to every count avoids dividing by zero for words that never appear elsewhere.

`heapq.nlargest(k, items, key=...)` is the efficient way to get the top *k* without sorting
everything. `attrgetter("lift")` is the standard library's `x => x.Lift`.

### 4. A small, immutable record type

```python
@dataclass(frozen=True, slots=True)
class Distinctive:
    word: str
    count: int
    lift: float
```

This is roughly a C# `record` or a TS `readonly` type. `frozen=True` makes instances immutable
and hashable, and `slots=True` drops the per-instance `__dict__`, so objects are smaller and
attribute access is faster. You get `__init__`, `__repr__` and `__eq__` for free. The tests use
that equality to compare whole `Source` objects in one assert.

### 5. The CLI returns an exit code

```python
def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    ...
    return 0
```

The script that `uv` generates for `[project.scripts]` calls `sys.exit(main())`, so returning
`2` sets the process exit code, like `static int Main`. Accepting `argv` lets the tests call
`main(["data/", "--json"])` directly, without spawning a process. `capsys` (a pytest fixture)
captures what was printed.

## If you wrote this in C# / TypeScript

| Task | C# | TypeScript | Python |
| --- | --- | --- | --- |
| Count occurrences | `CountBy(w => w)` (.NET 9) / `GroupBy` | `Map` + loop | `Counter(words)` |
| Top N | `OrderByDescending(..).Take(n)` | `.sort(..).slice(0, n)` | `counter.most_common(n)` |
| Merge counts | `Concat` + `GroupBy` + `Sum` | nested loops | `a + b` |
| Lazy sequence | `IEnumerable` + `yield return` | `function*` | generator function (`yield`) |
| Unicode letters | `\p{L}` | `\p{L}` with the `u` flag | `[^\W\d_]` (or the `regex` package) |
| Immutable record | `record Distinctive(...)` | `readonly` type | `@dataclass(frozen=True)` |
| Embedded file | `EmbeddedResource` | bundler asset import | `importlib.resources.files(...)` |
| CLI parsing | System.CommandLine | commander / yargs | `argparse` (standard library) |

The core in each language:

```csharp
// C# (.NET 9)
var top = Regex.Matches(text, @"\p{L}+(?:'\p{L}+)*")
    .Select(m => m.Value.ToLowerInvariant())
    .Where(w => w.Length >= 3 && !StopWords.Contains(w))
    .CountBy(w => w)
    .OrderByDescending(kv => kv.Value)
    .Take(10);
```

```typescript
// TypeScript
const counts = new Map<string, number>();
for (const [w] of text.matchAll(/\p{L}+(?:'\p{L}+)*/gu)) {
  const word = w.toLowerCase();
  if (word.length >= 3 && !STOP_WORDS.has(word)) counts.set(word, (counts.get(word) ?? 0) + 1);
}
const top = [...counts].sort((a, b) => b[1] - a[1]).slice(0, 10);
```

```python
# Python
counts = Counter(w for w in words(text) if len(w) >= 3 and w not in STOP_WORDS)
top = counts.most_common(10)
```

Python is shortest here because `Counter` *is* the "count by key" data structure. What's harder:
there's no `\p{L}` in `re`, and the type checker can't stop you from passing a `Counter` where a
plain `dict` was expected, or the reverse.

## Gotchas

- **Counter arithmetic drops zero and negative counts.** `Counter(a=1) - Counter(a=3)` is an empty
  `Counter()`, not `{'a': -2}`. Use `c.subtract(other)` if you need negative counts.
- **Generators are single-use.** After `Counter(words(text))` consumes the generator, iterating it
  again yields nothing, with no error. If you need the words twice, call `words(text)` again or
  build a list.
- **`sum()` of counters needs a start value.** `sum(counters)` starts from `0`, and `0 + Counter()`
  raises `TypeError`. Write `sum(counters, Counter())`.

## Your turn

1. **Easy:** add `--rarest`, which shows the least frequent words that still appear at least twice.
   Hint: `most_common()` with no argument returns everything sorted, so slicing with `[::-1]`
   reverses it.
2. **Medium:** add `--bigrams` to count word pairs such as `white whale`. Use
   `itertools.pairwise(words(text))`, and write a parametrized test for it.
3. **Stretch:** make stdin streaming, so `cat huge.log | wordfreq -` never holds the whole input in
   memory. Have `Source` carry an iterator of lines instead of one string. Measure the difference
   with `tracemalloc` on a generated 200 MB file.

## Go deeper

- [`collections.Counter`](https://docs.python.org/3/library/collections.html#collections.Counter)
- [argparse tutorial](https://docs.python.org/3/howto/argparse.html)
- [`importlib.resources`](https://docs.python.org/3/library/importlib.resources.html)
- [Regular expressions HOWTO](https://docs.python.org/3/howto/regex.html)
- Local lessons: lesson 02 (collections & comprehensions), lesson 06 (iterators & generators),
  lesson 13 (stdlib & ecosystem).
