# Day 006 · Markdown TOC Generator

`mdtoc` writes a table of contents into your Markdown files with anchors identical to the ones
GitHub generates, so every link works. It also checks your `#anchor` links and fails CI when
a TOC goes stale.

## Run it

```bash
cd py-md-toc
uv run mdtoc --check data/                        # CI mode: what's stale or broken, exit 1/2
uv run mdtoc --diff data/guide.md                 # what would change; touches nothing
uv run mdtoc data/                                # rewrite in place (git checkout data undoes it)
uv run mdtoc - < data/changelog.md                # stdin → stdout, for editors and pipes
uv run mdtoc -l 2-4 --diff ../py-todo-cli/README.md   # levels 2–4, on a real README
uv run mdtoc --check README.md                    # this lesson's own TOC, below
uv run pytest
```

The TOC lives between two HTML comments, which GitHub doesn't render:

```markdown
<!-- toc -->
- [Installation](#installation)
<!-- /toc -->
```

A file without markers gets them inserted above its first listed heading (`##` and `###` by
default). After that, each run replaces what's between the markers and nothing else.

## What it looks like

The sample [data/guide.md](data/guide.md) has front matter, a stale TOC, headings inside code
fences, a setext heading, three headings called `Example`, and a typo in a link:

```text
$ uv run mdtoc --check data/
mdtoc: data/broken.md:3: <!-- toc --> has no matching <!-- /toc -->
FAIL    data/changelog.md (TOC out of date)
data/guide.md:72: broken link #instalation (did you mean #installation?)
FAIL    data/guide.md (TOC out of date, 1 broken link)
```

```diff
$ uv run mdtoc --diff data/guide.md
--- a/data/guide.md
+++ b/data/guide.md
@@ -7,9 +7,20 @@
 <!-- toc -->
-- [Install](#install)
+- [Installation](#installation)
 - [Usage](#usage)
-  - [Old flags](#old-flags)
+  - [Brewing a V60 ☕](#brewing-a-v60-)
+  - [`brew --ratio` & friends](#brew---ratio--friends)
+  - [Example](#example)
+- [Configuration](#configuration)
+- [Environment variables](#environment-variables)
+  - [Example](#example-1)
+  - [`List<Recipe>` in the API](#listrecipe-in-the-api)
+- [FAQ](#faq)
+  - [Why is it called _Brewbot_?](#why-is-it-called-brewbot)
+  - [Q&A for C# / TypeScript folks](#qa-for-c--typescript-folks)
+  - [Example](#example-2)
+- [Troubleshooting](#troubleshooting)
 <!-- /toc -->
```

Look at the anchors. `brew---ratio--friends` has three hyphens, because `&` is deleted but the
spaces around it aren't. `brewing-a-v60-` ends in a hyphen where the emoji used to be.
`listrecipe` keeps the text inside the code span but drops the `<>`. That's GitHub's actual
algorithm, quirks included. Before writing this README I compared `mdtoc`'s slugs with the
`id`s GitHub renders for every heading already in this repo: 84 headings, 84 matches.

Point it at an earlier day and you get the TOC that README never had:

```diff
$ uv run mdtoc --diff ../py-expense-splitter/README.md
+<!-- toc -->
+- [Run it](#run-it)
 ...
+- [Code tour](#code-tour)
+  - [1. Splitting €100 three ways](#1-splitting-100-three-ways)
+  - [3. `defaultdict(Account)`: the ledger in six lines](#3-defaultdictaccount-the-ledger-in-six-lines)
 ...
+- [If you wrote this in C# / TypeScript](#if-you-wrote-this-in-c--typescript)
```

And this README's own TOC was written by `mdtoc`:

<!-- toc -->
- [Run it](#run-it)
- [What it looks like](#what-it-looks-like)
- [What you'll learn](#what-youll-learn)
- [Code tour](#code-tour)
  - [1. One regex, five constructs](#1-one-regex-five-constructs)
  - [2. A lazy pipeline: `prose` → `blocks`](#2-a-lazy-pipeline-prose--blocks)
  - [3. Matching the shape of the markers](#3-matching-the-shape-of-the-markers)
  - [4. GitHub's duplicate numbering, as a generator](#4-githubs-duplicate-numbering-as-a-generator)
  - [5. Rewriting a file in place without damaging it](#5-rewriting-a-file-in-place-without-damaging-it)
- [If you wrote this in C# / TypeScript](#if-you-wrote-this-in-c--typescript)
- [Gotchas](#gotchas)
- [Your turn](#your-turn)
- [Go deeper](#go-deeper)
<!-- /toc -->

## What you'll learn

- **Named groups everywhere**: `(?P<name>…)`, `m["name"]`, `(?P=name)` backreferences, and
  `m.lastgroup` to tell which branch of an alternation matched
  ([slugs.py#L13](src/py_md_toc/slugs.py#L13)).
- **`re.sub` with a function**: Python's `MatchEvaluator`, stripping inline Markdown in one
  pass ([slugs.py#L28](src/py_md_toc/slugs.py#L28)).
- **A generator pipeline**: `prose()` drops code and front matter, `blocks()` turns what's left
  into headings and markers, and nothing runs until someone iterates
  ([markdown.py#L50](src/py_md_toc/markdown.py#L50)).
- **Slugify, with state in a generator**: GitHub's duplicate numbering as one generator holding
  a dict of counts ([slugs.py#L50](src/py_md_toc/slugs.py#L50)).
- **`match` on a list of dataclasses**: marker validation as sequence and class patterns
  ([toc.py#L63](src/py_md_toc/toc.py#L63)).
- **An in-place rewrite that respects the file**: `newline=""` keeps CRLF, `copymode` keeps
  permissions, `os.replace` keeps it atomic ([files.py#L28](src/py_md_toc/files.py#L28)).

## Code tour

### 1. One regex, five constructs

```python
INLINE = re.compile(
    r"""
      `+ (?P<code> .+? ) `+                          # `List<int>` -> List<int>
    | !?\[ (?P<link> [^\]]* ) \] (?: \( [^)]* \) )?  # [text](url), ![alt](src), [ref] -> text
    | < /? [A-Za-z][^>]* >                           # <kbd>, </b> -> nothing (no group)
    | \\ (?P<escaped> [^\w\s] )                      # \_ -> _
    | (?<![\w\\]) (?P<marks> _{1,3} ) (?P<em> \S (?:.*?\S)? ) (?P=marks) (?!\w)  # _em_ -> em
    """,
    re.VERBOSE,
)


def plain_text(markdown: str) -> str:
    def keep_text(m: re.Match[str]) -> str:
        match m.lastgroup:
            case None:
                return ""
            case group:
                return m[group]

    return INLINE.sub(keep_text, markdown)
```

To slug a heading you first need its *rendered* text: `` `List<int>` `` renders as
`List<int>`, `<kbd>` renders as nothing. That's one regex with an alternative per construct,
and one replacement function.

- **Named groups are `(?P<name>…)`, with a `P`.** Python invented named groups (the `P` marks a
  Python-specific extension), and `re` still doesn't accept the `(?<name>…)` spelling that .NET
  and JS later standardised (see Gotchas). A named backreference is `(?P=marks)`: `_x_` and
  `__x__` match, `_x__` doesn't.
- **`m["name"]`** reads a group, same as `m.group("name")`, and is `None` if that group didn't
  take part in the match.
- **`m.lastgroup`** is the name of the last group that *closed*. Each alternative ends with exactly
  one "result" group (in the emphasis branch, `marks` closes before `em`), so `lastgroup` says
  which branch matched and `match` dispatches on it. The tag branch has no group at all, so
  `lastgroup` is `None` and the tag vanishes.
- **`re.sub` never rescans its replacements.** It walks the *original* string left to right, so
  once the code branch has consumed `` `List<int>` ``, the tag branch never sees `<int>`.
  Alternative order matters too: code comes first, so `` `[not a link](x)` `` stays code.

`re.VERBOSE` allows whitespace and comments in the pattern (.NET's
`RegexOptions.IgnorePatternWhitespace`, the `x` flag elsewhere), which is what makes a
five-branch pattern reviewable.

### 2. A lazy pipeline: `prose` → `blocks`

```python
def prose(lines: Sequence[str]) -> Iterator[tuple[int, str]]:
    ...
    fence: str | None = None
    for i, line in enumerate(lines[start:], start):
        m = FENCE.match(line)
        if fence is None:
            if m:
                fence = m["fence"]
            else:
                yield i, line
        # startswith() checks both at once: "````" closes "```", "~~~~" doesn't.
        elif m and m["fence"].startswith(fence) and not m["info"].strip():
            fence = None


def blocks(lines: Sequence[str]) -> Iterator[Heading | Marker]:
    previous: tuple[int, str] | None = None
    for i, line in prose(lines):
        if m := MARKER.match(line):
            yield Marker("open" if m["kind"].lower() == "toc" else "close", i)
        elif m := ATX.match(line):
            yield Heading(len(m["hashes"]), (m["text"] or "").strip(), i)
        elif (m := SETEXT.match(line)) and previous and previous[0] == i - 1:
            ...
```

A function containing `yield` returns an iterator, and its locals (`fence`, `previous`)
survive between `yield`s: C#'s `yield return`, with the same laziness. The difference is
culture. In Python this is the default shape for "a loop that produces things", and chaining
generators costs nothing until someone iterates.

The pipeline makes "headings inside code aren't headings" a decision taken once. `prose`
removes fenced code, so neither `blocks` nor `anchor_links` (which also reads from `prose`)
has to think about it. That's also why the `<!-- toc -->` example near the top of this README
didn't confuse `mdtoc` when it wrote this README's TOC: it's inside a fence.

`if m := ATX.match(line)` is the walrus operator (lesson 01): assign *and* test, so each regex
runs once and an `if`/`elif` chain over several regexes stays flat.

### 3. Matching the shape of the markers

```python
match markers:
    case []:
        return None
    case [Marker("open", start), Marker("close", end)]:
        return start, end
    case [Marker("open", start)]:
        raise TocError(start + 1, f"{OPEN} has no matching {CLOSE}")
    case [Marker("close", line), *_]:
        raise TocError(line + 1, f"{CLOSE} without an {OPEN} before it")
    case [Marker("open"), Marker("open", line), *_]:
        raise TocError(line + 1, f"a second {OPEN} before {CLOSE}")
    case _:
        raise TocError(markers[2].line + 1, "only one TOC per file is supported")
```

Day 2 matched lists of tokens, and day 5 matched dicts. Here a **sequence pattern** holds
**class patterns**: `Marker("open", start)` checks the type, compares the first field with the
literal `"open"`, and binds the second to `start`. Positional sub-patterns work because
`@dataclass` generates `__match_args__ = ("kind", "line")`. Every valid and invalid layout is
one line, and each error points at the marker that's actually wrong.

Case order *is* the logic. My first version put "three or more markers" before "two opens",
so `open, open, close` blamed line 3 instead of line 2. A parametrized test caught it.

Splicing the TOC in is slice assignment, which C# lists don't have:

```python
lines[start + 1 : end] = toc  # replace the old block, whatever its length
lines[first:first] = [OPEN, *toc, CLOSE, ""]  # assign to an empty slice: pure insertion
```

### 4. GitHub's duplicate numbering, as a generator

```python
def unique_slugs(headings: Iterable[str]) -> Iterator[str]:
    counts: dict[str, int] = {}
    for heading in headings:
        base = slug = slugify(heading)
        while slug in counts:
            counts[base] += 1
            slug = f"{base}-{counts[base]}"
        counts[slug] = 0
        yield slug
```

This is a port of `github-slugger`'s loop. Generated slugs are reserved *too*, so `Example`,
`Example`, `Example 1` give `example`, `example-1`, `example-1-1`: the third heading's natural
slug was already handed to the second. Numbering runs over *all* headings, including the `#`
title and the `####`s the TOC leaves out, so `update` slugs everything first and filters
afterwards. Filter first and every anchor after a hidden duplicate is off by one.

`slugify` itself is three steps: `plain_text`, `.lower()`, then
`re.sub(r"[^\w\- ]", "", …).replace(" ", "-")`. On a `str` pattern `\w` is Unicode, so `Łódź`
and `東京` survive while `·`, `&`, `€` and emoji go. And it's `.lower()`, not the `.casefold()`
of day 1: GitHub keeps `ß`, and `casefold()` would turn it into `ss` and break the link.

### 5. Rewriting a file in place without damaging it

```python
def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", newline="")


def write_text(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        shutil.copymode(path, tmp)  # mkstemp creates 0600; keep the original's permissions
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
```

Day 4 covered temp file + `os.replace`. Today adds what "in place" means for a file you don't
own:

- **`newline=""`** turns off *universal newlines*. By default text mode turns `\r\n` into `\n`
  on read and `\n` into `os.linesep` on write, so a Windows-authored README edited on a Mac
  silently becomes LF: a whole-file diff for a three-line change. `update` detects the file's
  newline itself, joins with it, and keeps a missing final newline missing.
- **`shutil.copymode`**, because `mkstemp` creates `0600` files, and swapping a `0644` README
  for a private one is a nasty surprise.
- **No write when nothing changed.** `Update.changed` compares the strings, so a clean run
  leaves mtimes alone and doesn't wake up watchers or `make`.

The stdlib also has `fileinput.input(inplace=True)`, which redirects `print()` into the file
line by line. It's handy for a quick script, but wrong here: it isn't atomic, it rewrites
unchanged files, and it streams line by line while a TOC needs the whole document first.

## If you wrote this in C# / TypeScript

| Task | C# | TypeScript | Python |
| --- | --- | --- | --- |
| Named group | `(?<name>…)` | `(?<name>…)` | `(?P<name>…)` |
| Named backreference | `\k<name>` | `\k<name>` | `(?P=name)` |
| Read a group | `m.Groups["name"].Value` | `m.groups.name` | `m["name"]` |
| Replace with a function | `Regex.Replace(s, MatchEvaluator)` | `s.replace(re, (m, …) => …)` | `re.sub(pattern, func, s)` |
| Which alternative matched | test each `Groups[…].Success` | test each group for `undefined` | `m.lastgroup` |
| Comments in a pattern | `RegexOptions.IgnorePatternWhitespace` | none (concatenate strings) | `re.VERBOSE` |
| Lazy sequence | `IEnumerable` + `yield return` | `function*` | generator function |
| Keep line endings | `File.ReadAllText` keeps them | `fs.readFileSync` keeps them | `open(…, newline="")` |
| Atomic replace | `File.Move(…, overwrite: true)` | `fs.renameSync` | `os.replace` |

Stripping inline code from a heading, side by side:

```csharp
// C#: a MatchEvaluator lambda
var text = Regex.Replace(heading, @"`+(?<code>.+?)`+", m => m.Groups["code"].Value);
```

```typescript
// TS: positional captures first, then offset, string, and finally the groups object
const text = heading.replace(/`+(?<code>.+?)`+/g, (...args) => args.at(-1).code);
```

```python
text = re.sub(r"`+(?P<code>.+?)`+", lambda m: m["code"], heading)
```

For today's features the three engines are equal. .NET's regex is genuinely more powerful
(balancing groups, right-to-left matching, source-generated `[GeneratedRegex]`), and JS has
`\p{L}` under the `u` flag, which Python's `re` lacks (the third-party `regex` module has it).
Python wins on ergonomics: `m["name"]`, `lastgroup`, and how naturally a regex sits inside a
generator or a `match`. The JS `replace` callback is the clumsiest of the three: named groups
arrive as the *last* argument, after a variable number of positional ones.

## Gotchas

- **`(?<name>…)` is a syntax error in Python.** `re.compile("(?<n>a)")` raises
  `re.PatternError: unknown extension ?<n`, so patterns pasted from C# or JS need the `P`.
  Don't confuse it with `(?<=…)` and `(?<!…)`, the lookbehinds, which *are* spelled the same in
  all three.
- **In `re.VERBOSE`, `#` starts a comment.** `^#{1,6}` in a verbose pattern silently becomes
  `^`. Write `[#]` or `\#`, as [markdown.py](src/py_md_toc/markdown.py#L14) does, and `[ ]`
  for a literal space.
- **`str.splitlines()` splits on more than newlines**: also `\v`, `\f`, `\x1c`–`\x1e`, `\x85`
  and U+2028/U+2029. Split and re-join a file with it and those characters come back as line
  breaks, so `update` uses `text.split(newline)`. (`splitlines(keepends=True)` is fine for
  `difflib`, where nothing is written back.)

## Your turn

1. **Easy:** add `mdtoc --anchors FILE`, which prints every heading at *all* levels as
   `line  #slug  text`, for when you're writing a link by hand. Test it on `data/guide.md`:
   the third `Example` must show `#example-2`.
2. **Medium:** per-file settings in the marker, `<!-- toc levels=2-4 -->`. Extend `MARKER` with
   an optional named group, reuse `parse_levels`, carry the range on `Marker`, and let it
   override `--levels`. A malformed setting gets its own `case` in `find_block` and a line
   number.
3. **Stretch:** cross-file link checking. When `mdtoc` runs over a directory, also check
   `[x](other.md#anchor)` and `[x](../py-todo-cli/README.md#gotchas)` against the target file's
   slugs. Cache each file's slugs with `functools.cache` keyed on the resolved `Path`, report a
   missing file differently from a missing anchor, then run it over the whole `python-daily`
   repo.

## Go deeper

- [`re` syntax](https://docs.python.org/3/library/re.html#regular-expression-syntax),
  [`Match.lastgroup`](https://docs.python.org/3/library/re.html#re.Match.lastgroup) and
  [`re.sub` with a function](https://docs.python.org/3/library/re.html#re.sub)
- [Regular Expression HOWTO](https://docs.python.org/3/howto/regex.html), especially verbose
  mode and search-and-replace
- [Generators](https://docs.python.org/3/howto/functional.html#generators) in the Functional
  Programming HOWTO
- [`open()` and its `newline` argument](https://docs.python.org/3/library/functions.html#open)
- [CommonMark spec](https://spec.commonmark.org/0.31.2/): ATX and setext headings, fenced code
- [github-slugger](https://github.com/Flet/github-slugger): the reference for GitHub's anchors
- Local lessons: lesson 06 (iterators and generators), lesson 08 (pattern matching), lesson 07
  (errors and context managers), lesson 13 (stdlib and ecosystem).
