# Day 007 · Disk Usage Explorer

`dux` shows what's eating your disk as a `du`-style tree, biggest first, with sub-character bars.
It counts bytes exactly the way `du` does, hard links and all, and can also stream out the N
largest files in constant memory.

## Run it

```bash
cd py-disk-usage
uv run dux data/sample                    # tree, 2 levels deep, bytes on disk
uv run dux data/sample -A -d 1            # apparent size (file lengths), 1 level
uv run dux data/sample -d 1 -e node_modules -e '.*'   # skip by glob, repeatable
uv run dux data/sample -l 3               # the 3 largest files instead of a tree
uv run dux .. -d 1 -n 5                   # the whole python-daily repo, top 5 per directory
uv run dux .. -l 4 --si                   # powers of 1000 (MB) instead of 1024 (MiB)
uv run pytest
```

Other flags: `-x` stays on one filesystem (like `du -x`), `-n` sets entries per directory
(default 8), `-d 0` prints just the total.

## What it looks like

[data/sample](data/sample) is a small fake project: logs, fonts, a `node_modules`, a dot
directory, and a symlink.

```text
$ uv run dux data/sample
 208.0 KiB  ████████████████████  100%  data/sample/  (14 files)
 104.0 KiB  ██████████             50%  ├── logs/
  68.0 KiB  █████████████▏         65%  │   ├── app.log
  36.0 KiB  ██████▉                35%  │   └── app.1.log
  64.0 KiB  ██████▏                31%  ├── assets/
  52.0 KiB  ████████████████▎      81%  │   ├── fonts/
  12.0 KiB  ███▊                   19%  │   └── hero.svg
  16.0 KiB  █▌                      8%  ├── node_modules/
   8.0 KiB  ██████████             50%  │   ├── is-odd/
   8.0 KiB  ██████████             50%  │   └── left-pad/
  12.0 KiB  █▏                      6%  ├── .cache/
  12.0 KiB  ████████████████████  100%  │   └── thumbs.bin
   8.0 KiB  ▊                       4%  ├── src/
   8.0 KiB  ████████████████████  100%  │   └── brewbot/
   4.0 KiB  ▍                       2%  ├── README.md
       0 B                          0%  └── latest.log -> logs/app.log

212,992 bytes on disk · scanned in 0.00s
```

Bars and percentages are relative to the parent, as in ncdu. Every size is a multiple of
4 KiB: that's *disk usage*, i.e. allocated blocks. A 736-byte README still occupies a whole
block. `-A` switches to apparent size, the file lengths `ls -l` shows:

```text
$ uv run dux data/sample -A -d 1
 181.1 KiB  ████████████████████  100%  data/sample/  (14 files)
 101.2 KiB  ███████████▏           56%  ├── logs/
  60.5 KiB  ██████▋                33%  ├── assets/
  12.1 KiB  █▍                      7%  ├── .cache/
   3.5 KiB  ▍                       2%  ├── node_modules/
   2.8 KiB  ▎                       2%  ├── src/
     736 B  ▏                       0%  ├── README.md
      12 B                          0%  └── latest.log -> logs/app.log
```

The symlink is 12 bytes: the length of the string `logs/app.log`. It's counted, never
followed. Now the whole repo, every day's `.venv` included:

```text
$ uv run dux .. -d 1 -n 5
 737.8 MiB  ████████████████████  100%  ../  (15,954 files)
 106.6 MiB  ██▉                    14%  ├── py-password-meter/
 106.5 MiB  ██▉                    14%  ├── py-unit-converter/
 106.5 MiB  ██▉                    14%  ├── py-word-frequency/
 106.4 MiB  ██▉                    14%  ├── py-todo-cli/
 103.8 MiB  ██▉                    14%  ├── py-disk-usage/
 208.0 MiB  █████▋                 28%  └── … 7 more

773,607,424 bytes on disk · scanned in 0.11s

$ du -sk ..
755476	..
```

773,607,424 / 1024 = 755,476 exactly, so `dux` agrees with `du` to the byte (a test checks
this too). And the largest files:

```text
$ uv run dux .. -l 4 --si
   40.3 MB  py-md-toc/.venv/lib/python3.14/site-packages/6ec57f84c680d3a3778b__mypyc.cpython-314-darwin.so
   40.3 MB  py-unit-converter/.venv/lib/python3.14/site-packages/6ec57f84c680d3a3778b__mypyc.cpython-314-darwin.so
   40.3 MB  py-disk-usage/.venv/lib/python3.14/site-packages/6ec57f84c680d3a3778b__mypyc.cpython-314-darwin.so
   40.3 MB  py-word-frequency/.venv/lib/python3.14/site-packages/6ec57f84c680d3a3778b__mypyc.cpython-314-darwin.so
```

That's mypy, compiled with mypyc, once per day. Is it really seven copies? On Linux, uv
hard-links packages from its cache, so they'd share one inode and `dux` would count them once.
On macOS uv uses APFS *clones* instead: separate inodes that share blocks copy-on-write. No
`stat()` field reveals that sharing, so `du`, Finder and `dux` all count each clone in full.
737 MiB is the honest `du` answer, and also an overestimate.

When something can't be read, you still get the rest, plus a message and exit code 1, like
`du`:

```text
$ uv run dux /tmp/locked-demo -d 1
  12.0 KiB  ████████████████████  100%  /tmp/locked-demo/  (1 file)
  12.0 KiB  ████████████████████  100%  ├── public/
       0 B                          0%  └── secret/  [Permission denied]

12,288 bytes on disk · scanned in 0.00s
dux: /tmp/locked-demo/secret: Permission denied
```

## What you'll learn

- **`__format__`, i.e. extending the format-spec mini-language**: `f"{size:>10.1h}"` works
  because `Size` parses the spec itself and hands everything it doesn't own to `int`
  ([size.py#L32](src/py_disk_usage/size.py#L32)).
- **Subclassing a built-in, and its traps**: `int`'s operators return plain `int`, and `int`
  has no `__str__` of its own ([size.py#L45](src/py_disk_usage/size.py#L45)).
- **Recursion over `os.scandir`**: totals fall out of return values, `DirEntry` caches what the
  OS already told you, `with` closes the handle ([scan.py#L85](src/py_disk_usage/scan.py#L85)).
- **`os.walk` as a flat generator**: prune by assigning to `dirnames[:]`, and stream into
  `heapq.nlargest` in O(n) memory ([walk.py#L37](src/py_disk_usage/walk.py#L37)).
- **Recursive generators with `yield from`**: the tree renderer, which also nests one format
  spec inside another ([render.py#L49](src/py_disk_usage/render.py#L49)).
- **`du`'s accounting**: `st_blocks * 512`, hard links deduplicated on `(st_dev, st_ino)`
  ([scan.py#L54](src/py_disk_usage/scan.py#L54)).

## Code tour

### 1. A number that formats itself

```python
HUMAN_SPEC = re.compile(
    r"""
    (?P<align> (?: .? [<>^] )? )
    (?P<width> \d* )
    (?: \. (?P<precision> \d+ ) )?
    (?P<kind> [hH] )
    """,
    re.VERBOSE,
)


class Size(int):
    __slots__ = ()

    def __format__(self, spec: str) -> str:
        m = HUMAN_SPEC.fullmatch(spec)
        if m is None:
            return super().__format__(spec)  # ",", "_", ">12", "x", "" ... all int's business
        precision = int(m["precision"] or 1)
        base, units = (1024, BINARY) if m["kind"] == "h" else (1000, DECIMAL)
        text = human(self, base, units, precision)
        # Strings default to left-aligned; a column of sizes should line up on the right.
        return format(text, f"{m['align'] or '>'}{m['width']}")
```

Everything after the `:` in `f"{x:spec}"` is passed, as a string, to `type(x).__format__`.
The language doesn't interpret it at all. `int`, `float`, `str`, `datetime` and `Decimal` each
parse their own mini-language, which is why `f"{now:%Y-%m-%d}"` works. So a class can add
presentation types of its own:

```python
>>> s = Size(1_572_864)
>>> f"{s:h}|{s:.2h}|{s:H}|{s:>10.1h}|{s:*^11.0h}|{s:,}|{s:x}"
'1.5 MiB|1.50 MiB|1.6 MB|   1.5 MiB|***2 MiB***|1,572,864|180000'
```

The last two are plain `int` formatting, untouched. Here the format spec is a public API
that you extend; it isn't a fixed list of codes.

The width is your job. C# splits `{x,10:h}` into alignment (handled by the framework) and
format (handled by the type). Python sends the whole spec to the type, so `Size` strips off its
own part and reformats the resulting *string* with what's left: `format(text, ">10")`.

`human()` has one subtle line: it compares *after* rounding. 1,048,575 bytes is 1023.999 KiB,
which prints as `1024.0 KiB` unless you check the rounded value and move up a unit
(`1.0 MiB`). A parametrized test pins it down.

### 2. Recursion: the totals fall out of the call stack

```python
def visit(path: str, name: str, st: os.stat_result) -> Node:
    own = Size(usage(st, apparent=options.apparent) if first_sighting(st, seen) else 0)
    ...
    node = Node(name, own, is_dir=True)
    try:
        with os.scandir(path) as entries:  # `with` closes the OS handle even on error
            for entry in entries:
                if excluded(entry.name, options.exclude):
                    continue
                try:
                    child = entry.stat(follow_symlinks=False)
                except OSError as e:
                    problems.append(Problem.of(e))
                    continue
                ...
                node.children.append(visit(entry.path, entry.name, child))
    except OSError as e:  # PermissionError on open, or an I/O error mid-listing
        node.error = e.strerror
        problems.append(Problem.of(e))

    node.size += sum(c.size for c in node.children)
    node.files = sum(c.files for c in node.children)
    node.children.sort(key=lambda c: (-c.size, c.name))
    return node
```

A directory's size is its own size plus what its children *return*. That's a recursive
definition, so the recursive code is the shortest. `visit` is a closure inside `scan()`, so
`seen`, `problems` and `options` are shared state without a class (no `DiskScanner` with
three fields and one method).

`os.scandir` yields `DirEntry` objects. The OS already returned each name together with its
type when it listed the directory, so `entry.is_dir()` costs no system call, and
`entry.stat()` is cached on the entry. On Windows even the full `stat` comes free with the
listing. That's PEP 471, and it's why `os.walk` has been built on `scandir` since 3.5. Since
3.14, `Path.iterdir()` uses the same trick: each `Path` it yields carries a cached
`path.info`.

I measured four traversals of this repo (15,954 files, warm cache, macOS): `scan()` 110 ms,
`os.walk` + `lstat` 105 ms, `os.listdir` + `lstat` 120 ms, `Path.rglob("*")` + `lstat`
130 ms. They're close because sizing a file needs a stat whichever way you list it. The big
wins for `scandir` are on Windows and for code that only needs types.

Errors are part of the design. Both `try` blocks turn an `OSError` into a `Problem` and keep
going, because a disk-usage tool that dies on one locked folder is useless. The outer `try`
also catches errors *during* iteration, so children read before the failure are kept.

### 3. `os.walk`: when you don't need a tree

```python
for dirpath, dirnames, filenames in os.walk(root, onerror=report):
    # Prune *in place*: os.walk recurses into whatever this same list holds after the yield.
    # `dirnames = [...]` would rebind a local name and prune nothing.
    dirnames[:] = [
        d
        for d in dirnames
        if not excluded(d, options.exclude)
        and not (options.one_file_system and other_device(dirpath, d, top_dev))
    ]
    for name in filenames:
        ...
        if first_sighting(st, seen):
            yield File(path, Size(usage(st, apparent=options.apparent)))
```

```python
return heapq.nlargest(n, iter_files(root, options, on_error), key=attrgetter("size"))
```

`os.walk` is flat: one `(dirpath, dirnames, filenames)` triple per directory, with no parent
totals. For "the 10 biggest files" that's exactly right. `iter_files` is a generator, and
`heapq.nlargest` keeps a heap of `n` items, so `dux -l 10` holds ten `File`s in memory however
many million it walks past. That's `.OrderByDescending(f => f.Size).Take(10)` without the
full sort.

`dirnames[:] = …` is the classic idiom. `os.walk` yields its own list object and reads it
back to decide where to go next, so you prune by mutating that object. Slice assignment
replaces the list's contents in place (you saw it on day 6).

Errors go through `onerror=report` and then to a callback, `on_error`. The CLI passes
`problems.append`, a bound method, so there's no lambda and no interface: any callable that
takes a `Problem` will do (`Callable[[Problem], object]`).

So why isn't the tree built with `os.walk` too? You can (it's the medium challenge below),
with `topdown=False` and a dict of totals keyed by path. But then you rebuild the hierarchy
that recursion gave you for free.

### 4. A recursive generator renders the tree

```python
def row(size: Size, fraction: float, label: str, unit: Unit) -> str:
    return f"{size:>10.1{unit}}  {bar(fraction)}  {fraction:>4.0%}  {label}"


def branch(parent: Node, depth: int, limit: int, unit: Unit, indent: str) -> Iterator[str]:
    if depth <= 0:
        return
    shown, hidden = parent.children[:limit], parent.children[limit:]
    for i, child in enumerate(shown):
        last = i == len(shown) - 1 and not hidden
        fraction = share(child.size, parent.size)
        yield row(child.size, fraction, f"{indent}{'└── ' if last else '├── '}{label(child)}", unit)
        yield from branch(child, depth - 1, limit, unit, indent + ("    " if last else "│   "))
    if hidden:
        rest = sum((c.size for c in hidden), start=Size(0))  # start= keeps the result a Size
        ...
```

`yield from branch(...)` re-yields everything the recursive call produces. It's TS's
`yield*`; C# has no equivalent, so there you'd write `foreach (var line in Branch(...)) yield
return line;`. The renderer never builds a list of lines: `main` prints each one as it's
produced, and the tests take `next(render(root))` to read only the first.

`row` shows three format-spec features in one line:

- **A nested replacement field**: `{size:>10.1{unit}}`. The `{unit}` inside the spec is
  filled in first, so `Size.__format__` receives `">10.1h"` or `">10.1H"`.
- **`%` as a presentation type**: `{0.513:>4.0%}` is ` 51%`. It multiplies by 100 for you.
- **`Literal["h", "H"]`** as the type of `unit`, declared with the 3.12 `type` statement,
  so mypy rejects `unit="x"` before it ever reaches `__format__`.

The bar uses Unicode eighth-blocks (`▏▎▍▌▋▊▉█`), so a 20-character bar has 160 steps. Without
them, everything under 5% is an empty bar. It's one `divmod`:

```python
eighths = round(min(max(fraction, 0.0), 1.0) * width * 8)
full, part = divmod(eighths, 8)
return ("█" * full + EIGHTHS[part].strip()).ljust(width)
```

### 5. Counting like `du`

```python
def usage(st: os.stat_result, *, apparent: bool) -> int:
    if apparent or sys.platform == "win32":
        return st.st_size
    return st.st_blocks * 512  # POSIX st_blocks is in 512-byte units, whatever the fs block size


def first_sighting(st: os.stat_result, seen: set[tuple[int, int]]) -> bool:
    if st.st_nlink < 2 or stat.S_ISDIR(st.st_mode):  # every directory has nlink >= 2
        return True
    key = (st.st_dev, st.st_ino)
    if key in seen:
        return False
    seen.add(key)
    return True
```

Two facts make the totals match `du`:

- **Blocks, not lengths.** `st_blocks` counts allocated 512-byte units, so a 1-byte file costs
  4 KiB, and a sparse 10 GB VM image costs only what's actually written. The
  `sys.platform == "win32"` check isn't only a runtime branch: mypy narrows on it, and
  `st_blocks` doesn't exist in the Windows stubs.
- **A hard-linked file is counted once.** Its identity is `(device, inode)`, a tuple, and
  that tuple is the set key, with no `GetHashCode` override needed. Only files with
  `st_nlink > 1` go into the set, so memory stays small.

## If you wrote this in C# / TypeScript

| Task | C# | TypeScript (Node) | Python |
| --- | --- | --- | --- |
| Custom format code | `IFormattable.ToString(format, provider)` | none (`toString()` only) | `__format__(self, spec)` |
| Alignment in a placeholder | `{x,10:h}`, done by the framework | `padStart(10)` | `{x:>10h}`, passed to the type |
| List a directory with types | `DirectoryInfo.EnumerateFileSystemInfos()` | `fs.readdir(p, { withFileTypes: true })` | `os.scandir(p)` |
| Whole-tree enumeration | `EnumerateFiles(…, SearchOption.AllDirectories)` | `fs.readdir(p, { recursive: true })` | `os.walk(p)`, `Path.walk()`, `Path.rglob("*")` |
| Allocated size, inode, link count | not in the BCL (P/Invoke) | `fs.lstat`: `blocks`, `ino`, `nlink` | `os.lstat`: `st_blocks`, `st_ino`, `st_nlink` |
| Recursive iterator | `foreach (…) yield return x;` | `yield*` | `yield from` |
| Top N without a full sort | `PriorityQueue<T, TPriority>` by hand, or `OrderBy().Take()` | sort, or a heap library | `heapq.nlargest(n, it, key=…)` |

A custom format code, side by side:

```csharp
readonly record struct Size(long Bytes) : IFormattable
{
    public string ToString(string? format, IFormatProvider? provider) => format switch
    {
        "h" => Human(Bytes, 1024),
        _ => Bytes.ToString(format, provider),
    };
}
// $"{size,10:h}": the framework pads to 10, ToString only ever sees "h"
```

```python
class Size(int):
    # f"{size:>10h}": __format__ receives ">10h" whole, so it parses and pads by itself
    def __format__(self, spec: str) -> str: ...
```

C# got the division of labour right, since alignment is never your problem. Python's
advantage is that `Size` *is* an `int`: it compares, sorts, sums and serialises to JSON like
one, with no `.Bytes` everywhere. Node's `fs` is honestly the closest match to Python here. It
exposes `blocks` and `ino` too, while .NET hides them behind `FileInfo.Length`, so an exact
`du` clone in C# needs platform calls.

## Gotchas

- **Subclassing `int` is leakier than it looks.** Every operator returns a plain `int`:
  `Size(1) + Size(2)` would be `3`, and `f"{a + b:h}"` would then raise `ValueError: Unknown
  format code 'h' for object of type 'int'`. That's why `Size` overrides `__add__`, `__radd__`
  and `__sub__` (but not `*`: `Size(5) * 2` is still an `int`). And `int` has no `__str__` of
  its own; it inherits `object.__str__`, which calls `repr()`. My first version only overrode
  `__repr__`, and the 0-byte symlink printed as `Size(0) B`.
- **`dirnames = [...]` silently prunes nothing.** Inside an `os.walk` loop, rebinding the name
  leaves `os.walk`'s list untouched. It has to be `dirnames[:] = ...`, or `.remove()`/`del`
  on the list itself. Pruning also only works with `topdown=True` (the default). Bottom-up,
  the subdirectories were already visited.
- **A generator's errors are lazy.** `iter_files(Path("missing"), …)` raises nothing. The
  `FileNotFoundError` arrives on the first `next()`, wherever that happens to be (see
  `test_generator_errors_are_lazy`). Wrap the *iteration* in `try`, not the call. Or, if you
  want eager validation, split the function in two: a regular function that checks, and
  returns an inner generator.

Also: `scan()` recurses once per directory level, and Python's default recursion limit is
1,000. Real trees almost never get that deep (`main` turns a `RecursionError` into an error
message just in case). `os.walk` itself has used an explicit stack since 3.12, so it has no
such limit.

## Your turn

1. **Easy:** `--min-size 1M` hides entries smaller than a threshold. Write `parse_size("1.5M")`
   as the inverse of `human()` (accept `K`/`M`/`G`, with an optional `iB` or `B`, and powers of
   1024), pass it to argparse as `type=parse_size` so bad input gets a proper usage error, and
   in `branch()` fold the small entries into the `… N more` row. Parametrize the tests,
   including `"0"` and `"12 MiB"`.
2. **Medium:** `dux --flat` prints a classic `du -h` listing: every directory with its total,
   deepest first. Build it on `os.walk(root, topdown=False)` with a `dict[str, int]` of totals.
   Each directory adds its files plus its subdirectories' already-computed totals. Then write a
   test that checks it against `scan()` on the `tree` fixture for every directory.
3. **Stretch:** make `scan()` iterative, so depth is unlimited. Use an explicit stack of
   `(node, scandir-iterator)` pairs, and roll sizes up into the parent when an iterator runs
   dry. Test it with `sys.setrecursionlimit(100)` (restored in a `finally`) and a 300-level
   tree of `d/d/d/…` in `tmp_path`. The recursive version must raise `RecursionError` and the
   new one must return the right `files` count.

## Go deeper

- [`object.__format__`](https://docs.python.org/3/reference/datamodel.html#object.__format__)
  and the [Format Specification
  Mini-Language](https://docs.python.org/3/library/string.html#formatspec), including
  nested replacement fields
- [`os.scandir` and `DirEntry`](https://docs.python.org/3/library/os.html#os.scandir), and
  [PEP 471](https://peps.python.org/pep-0471/) for why it exists
- [`os.walk`](https://docs.python.org/3/library/os.html#os.walk) (read the pruning notes),
  [`Path.walk`](https://docs.python.org/3/library/pathlib.html#pathlib.Path.walk) and
  [`Path.info`](https://docs.python.org/3/library/pathlib.html#pathlib.Path.info) (new in 3.14)
- [PEP 380](https://peps.python.org/pep-0380/): `yield from`
- [`heapq.nlargest`](https://docs.python.org/3/library/heapq.html#heapq.nlargest)
- [`os.stat_result`](https://docs.python.org/3/library/os.html#os.stat_result): `st_blocks`,
  `st_ino`, `st_nlink`
- Local lessons: lesson 04 (classes and OOP: dunder methods), lesson 06 (iterators and
  generators), lesson 13 (stdlib and ecosystem).
