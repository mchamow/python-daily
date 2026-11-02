# Day 009 · Cipher Toolkit

`cipher` encrypts and decrypts with Caesar, Vigenère and Atbash. Its `crack` command breaks
all three **without the key**. It works out how long the Vigenère keyword is, recovers it one
letter at a time, and prints the plaintext, using nothing but letter counts.

## Run it

```bash
cd py-cipher-toolkit
uv run cipher crack -f data/secret.txt --explain    # the wow moment: find the key, then decrypt
uv run cipher crack -f data/short.txt               # a short Caesar message, with runners-up
uv run cipher caesar -s 3 "Hello, World!"           # -d decrypts; any int works, even -3 or 1000
uv run cipher vigenere -k LEMON "Attack at dawn!"   # -d decrypts
uv run cipher atbash "Wizard"                       # a↔z, b↔y …: its own inverse
uv run cipher freq -f data/message.txt              # letter frequencies vs. English
uv run cipher atbash -f data/message.txt | uv run cipher crack   # text from stdin works too
uv run pytest
```

Text comes from the argument, then `-f FILE`, then stdin. `data/message.txt` is a plaintext.
`data/secret.txt` is the same text under a Vigenère key, made with `cipher vigenere`. The key
isn't written down anywhere: let `cipher crack` find it.

## What it looks like

The cracker on `data/secret.txt`, a 517-letter Vigenère ciphertext:

```
$ uv run cipher crack -f data/secret.txt --explain
Key length vs. mean index of coincidence of its columns
(English ≈ 0.065, random ≈ 0.038)
    1  0.0425  ███████▉
    2  0.0453  █████████▉
    3  0.0532  ███████████████▏
    4  0.0455  █████████▉
    5  0.0408  ██████▊
    6  0.0683  █████████████████████████▎      ← key length
    7  0.0427  ████████
    8  0.0448  █████████▍
    9  0.0542  ███████████████▊
   10  0.0452  █████████▊
   11  0.0431  ████████▎
   12  0.0681  █████████████████████████▏
   …
   18  0.0700  ██████████████████████████▍
   19  0.0382  █████
   20  0.0472  ███████████

Best guess: Vigenère, key WALRUS  (χ² 16.2)
Meet me at the old lighthouse on the north pier at midnight on Friday. Bring the brass key
from the drawer under the stairs, a torch with fresh batteries and a warm coat, because the
wind off the water is brutal this time of year. Do not tell anyone where you are going, not
…
and we never speak of it again.

Runners-up (χ²: lower is more English):
    1,617.7  Caesar, shift 24 (decrypt with -s -24)   Kgrm iy yv gaa ijf ybcbrjbnoy mp gaa hmtga lcct …
    2,113.2  Caesar, shift 17 (decrypt with -s -17)   Rnyt pf fc nhh pqm fijiyqiuvf tw nhh otanh sjja …
    2,237.7  Caesar, shift 18 (decrypt with -s -18)   Qmxs oe eb mgg opl ehihxphtue sv mgg nszmg riiz …
```

Look at the chart. Lengths 6, 12 and 18 all light up, and 18 is actually the tallest. They are
the key length and its multiples. Lengths 3 and 9 glow faintly, because they share a factor
with 6. The cracker takes the *shortest* strong length, which is 6. The whole run takes about
80 ms, most of it interpreter start-up.

A short message is harder, and the tool says so. There are not enough letters for the counts
to settle, so a 6-letter Vigenère "key" that overfits the noise comes a close second:

```
$ uv run cipher crack -f data/short.txt
Only 65 letters: the guesses below are shaky.

Best guess: Caesar, shift 7 (decrypt with -s -7)  (χ² 22.5)
Never trust a lighthouse keeper who says he has seen nothing in the fog tonight.

Runners-up (χ²: lower is more English):
       29.4  Vigenère, key HUHWHH                     Nrvpr trhse a lithehoufe veeprr hho snyd he hns …
      145.8  Caesar, shift 20 (decrypt with -s -20)   Arire gehfg n yvtugubhfr xrrcre jub fnlf ur unf …
      197.8  Caesar, shift 13 (decrypt with -s -13)   Hypyl nlomn u fcabnbiomy eyyjyl qbi musm by bum …
```

The everyday commands keep case and punctuation. They pass non-English letters through
untouched, and the key skips over spaces:

```
$ uv run cipher caesar -s 3 "Hello, World! Zażółć gęślą jaźń"
Khoor, Zruog! Cdżółć jęśoą mdźń
$ uv run cipher vigenere -k LEMON "Attack at dawn!"
Lxfopv ef rnhr!
$ uv run cipher vigenere -d -k LEMON "Lxfopv ef rnhr!"
Attack at dawn!
$ uv run cipher atbash "Wizard"
Draziw
$ uv run cipher vigenere -k "s3cret" hello
usage: cipher [-h] {caesar,vigenere,atbash,freq,crack} ...
cipher: error: a key must be ASCII letters only, got 's3cret'
```

`freq` shows why Caesar can't hide anything, and why Vigenère can. On the plaintext the bars
follow the English markers (`┆`):

```
$ uv run cipher freq -f data/message.txt
517 letters, index of coincidence 0.0686
(English ≈ 0.0655, random letters ≈ 0.0385)  ┆ = English
  a   7.2% ████████████████████   ┆                   8.2%
  b   1.7% ████▉                                      1.5%
  c   2.1% ██████  ┆                                  2.8%
  d   3.3% █████████▎  ┆                              4.3%
  e  14.3% ████████████████████████████████████████  12.7%
  …
```

On the Vigenère ciphertext they flatten: *e* falls to 7.2%, rare letters like *j* rise, and
the index of coincidence drops towards random:

```
$ uv run cipher freq -f data/secret.txt
517 letters, index of coincidence 0.0425
(English ≈ 0.0655, random letters ≈ 0.0385)  ┆ = English
  a   4.6% ██████████████▋           ┆                8.2%
  b   1.4% ████▎┆                                     1.5%
  c   3.3% ██████████▍                                2.8%
  d   4.4% ██████████████                             4.3%
  e   7.2% ██████████████████████▌                ┆  12.7%
  …
  j   3.7% ███████████▋                               0.2%
  …
```

## What you'll learn

- **`str.maketrans` + `str.translate`**: a whole-string character map that runs in C. It is
  138× faster here than an `ord`/`chr` loop
  ([ciphers.py#L18](src/py_cipher_toolkit/ciphers.py#L18)).
- **`@functools.cache`** as a zero-ceremony memo table for the 26 shift tables
  ([ciphers.py#L17](src/py_cipher_toolkit/ciphers.py#L17)).
- **`itertools.cycle`** plus a generator, so the key repeats forever and only advances on
  letters ([ciphers.py#L58](src/py_cipher_toolkit/ciphers.py#L58)).
- **Extended slices**: `letters[i::n]` *is* the i-th Vigenère column, with no loops or index
  maths ([crack.py#L73](src/py_cipher_toolkit/crack.py#L73)).
- **`Counter`** for statistics: `.total()`, missing keys count as 0, and chi-squared plus the
  index of coincidence in one line each
  ([analysis.py#L35](src/py_cipher_toolkit/analysis.py#L35)).
- **`zip(strict=True)`**, a `type` alias over a `Literal`, and `match` with a guard
  ([report.py#L31](src/py_cipher_toolkit/report.py#L31),
  [crack.py#L39](src/py_cipher_toolkit/crack.py#L39)).

## Code tour

### 1. A translation table instead of character arithmetic

The C# reflex is `(char)((c - 'a' + shift) % 26 + 'a')` in a loop. Python's idiom is to build
the mapping once and let `str.translate` apply it:

```python
@cache
def shift_table(shift: int) -> dict[int, int]:
    s = shift % 26  # Python's % is never negative here: -3 % 26 == 23 (C# gives -3)
    lower = ascii_lowercase[s:] + ascii_lowercase[:s]
    return str.maketrans(ascii_lowercase + ascii_uppercase, lower + lower.upper())


def caesar(text: str, shift: int) -> str:
    return text.translate(shift_table(shift))
```

- **Two equal-length strings.** `str.maketrans(a, b)` pairs them position by position, like
  `dict(zip(a, b))`. It returns a `dict[int, int]` from code point to code point. A third
  argument lists characters to delete.
- **Rotation is slicing.** `ascii_lowercase[s:] + ascii_lowercase[:s]` rotates the alphabet.
  Atbash is the same call with `ascii_lowercase[::-1]`.
- **Anything missing passes through.** Characters not in the table, like digits, spaces or
  `ż`, come out unchanged. That's why there's no `if c.isalpha()` branch.
- **`@cache` is the memo table.** There are only 26 tables, so it is effectively a lazy
  `static readonly Dictionary<int, ...>`, built on demand. It needs no class and no explicit
  key.

To measure the speed, I compared it with the version you'd write from C# muscle memory. This
loop is only the benchmark; it isn't in the app:

```python
for c in text:
    if "a" <= c <= "z":
        out.append(chr((ord(c) - 97 + k) % 26 + 97))
    elif "A" <= c <= "Z":
        out.append(chr((ord(c) - 65 + k) % 26 + 65))
    else:
        out.append(c)
```

On 132,400 characters, `translate` took **0.16 ms** and this loop took **21 ms**, about 138×
slower. The loop would be fine in C#, because the JIT turns it into tight machine code. In
CPython every iteration is interpreted bytecode, so the Pythonic move is to push the loop into
a C-level builtin: `translate`, `str.join`, `sum`, `Counter`, slicing.

### 2. `cycle` and a key that skips punctuation

```python
def vigenere(text: str, key: str, *, decrypt: bool = False) -> str:
    sign = -1 if decrypt else 1
    shifts = cycle(sign * s for s in key_shifts(key))

    def chars() -> Iterator[str]:
        for ch in text:
            yield ch.translate(shift_table(next(shifts))) if ch in LETTERS else ch

    return "".join(chars())
```

- **An endless key stream.** `itertools.cycle` turns `[11, 4, 12, 14, 13]` into
  `11, 4, 12, 14, 13, 11, 4, …`. Because it is an iterator, you pull from it with `next()`
  only when you need a value. Here that's only for letters, so `"attack at dawn"` uses the
  same key letters as `"ATTACKATDAWN"`. With `zip(text, cycle(key))` the spaces would eat key
  letters. That is a common bug in Vigenère code.
- **The C# version** would keep an `int keyIndex` and write `keyIndex++ % key.Length`.
  `cycle` makes the "position in the key" state invisible.
- **Reuse.** The per-character `translate` reuses the cached Caesar tables, so Vigenère really
  is "a different Caesar per letter" in code, too.
- **`*, decrypt`** makes `decrypt` keyword-only. That avoids the mystery-boolean
  `vigenere(t, k, True)`, the Python cousin of C#'s named arguments.
- **`LETTERS` is a `frozenset`**, not `str.isalpha`, for the reason in the gotchas below.

### 3. A Vigenère column is a slice

Here is the whole insight of the attack. With a key of length n, letters 0, n, 2n … were all
shifted by the same key letter, so together they form a plain Caesar cipher. In Python that
column is `letters[i::n]`: start at i, step n.

```python
def key_length_scores(letters: str, max_length: int) -> dict[int, float]:
    longest = min(max_length, len(letters) // MIN_PER_COLUMN)
    return {
        n: fmean(index_of_coincidence(letters[i::n]) for i in range(n))
        for n in range(1, max(longest, 1) + 1)
    }


def likely_key_length(scores: dict[int, float], tolerance: float = 0.9) -> int:
    best = max(scores.values())
    return next(n for n, score in scores.items() if score >= best * tolerance)
```

- **The index of coincidence** asks: "if I pick two letters from this column at random, how
  likely are they to be the same?" It ignores *which* letters are common, so a Caesar shift
  can't change it. At the right n every column is shifted English (≈0.066). At a wrong n each
  column mixes several shifts and looks random (≈0.038).
- **Multiples of the true length** (12, 18) score just as high, and sometimes higher, since
  shorter columns are noisier. So `likely_key_length` picks the *first* score within 10% of
  the best. `next(generator)` is Python's `First(predicate)`. Without a default it raises
  `StopIteration`, but here the maximum always qualifies.
- **Breaking it.** Once n is known, `_undo` runs the Caesar breaker on each `letters[i::n]`.
  It then calls `shortest_period` in case n was a multiple, so a recovered `WALRUSWALRUS`
  becomes `WALRUS`.

### 4. Statistics with `Counter`

```python
def chi_squared(counts: Counter[str]) -> float:
    n = counts.total()
    if n == 0:
        return float("inf")
    return sum((counts[c] - n * p / 100) ** 2 / (n * p / 100) for c, p in ENGLISH.items())


def rank_shifts(letters: str) -> list[tuple[int, float]]:
    scores = {s: chi_squared(Counter(letters.translate(shift_table(-s)))) for s in range(26)}
    return sorted(scores.items(), key=lambda item: item[1])
```

- **No `TryGetValue` dance.** `counts[c]` on a letter that never appeared returns `0`, not a
  `KeyError`.
- **`Counter.total()`** (3.10+) sums the counts. On older code you'll see
  `sum(c.values())`.
- **Breaking Caesar** means trying every shift and sorting by how English the result looks.
  Day 1 used `Counter.most_common()`. Here the counts feed a formula instead.
- **`float("inf")`** for "no letters" sorts last without a special case.
- **`ENGLISH` is a dict literal under `# fmt: skip`**, so ruff keeps the hand-aligned
  seven-letters-per-row table. `Final` tells mypy the name is never rebound.

### 5. Candidates: a `Literal` alias, `match` with a guard, dedupe with a dict

```python
type CipherName = Literal["caesar", "vigenere", "atbash"]


def describe(self) -> str:
    match self.cipher:
        case "caesar" if self.key == "A":
            return "not encrypted (Caesar shift 0)"
        case "caesar":
            shift = ascii_uppercase.index(self.key)
            return f"Caesar, shift {shift} (decrypt with -s {-shift})"
        case "vigenere":
            return f"Vigenère, key {self.key}"
        case "atbash":
            return "Atbash"
```

- **Exhaustiveness.** mypy knows `self.cipher` can only be those three strings, so it accepts
  the `match` with no fallback `return`. This is TypeScript's string-literal union, with
  `match` standing in for `switch` plus the `never` exhaustiveness check.
- **Dedupe.** `crack()` collects the best Vigenère guess, the top 3 Caesar shifts and Atbash.
  For a Caesar text the "Vigenère" guess *is* a Caesar guess (key length 1), so
  `{(c.cipher, c.key): c for c in found}.values()` drops the duplicate. Dicts keep insertion
  order, so this is LINQ's `DistinctBy` in one expression.

## If you wrote this in C# / TypeScript

| Task | C# | TypeScript | Python |
| --- | --- | --- | --- |
| Map characters | a `char` loop into `StringBuilder` | `[...s].map(...).join("")` | `s.translate(table)`, in C |
| Build the map | `Dictionary<char, char>` | `Map<string, string>` | `str.maketrans("abc", "xyz")` |
| Repeat a key forever | `keyIndex++ % key.Length` | same | `itertools.cycle(key)` + `next()` |
| Every n-th element from i | `s.Where((c, j) => j % n == i)` | `[...s].filter((_, j) => j % n === i)` | `s[i::n]` |
| Count letters | `GroupBy(c => c).ToDictionary(...)` | `reduce` into an object | `Counter(s)` |
| Memoize a pure function | a `ConcurrentDictionary` cache | a `Map` cache | `@functools.cache` |
| Zip, insisting on equal lengths | `Zip`, which truncates silently | no built-in `zip` | `zip(a, b, strict=True)` |
| A closed set of names | `enum`, or `const` strings | `"a" \| "b" \| "c"` | `type T = Literal["a", "b", "c"]` |

The column split, side by side:

```csharp
var columns = Enumerable.Range(0, n)
    .Select(i => new string(letters.Where((_, j) => j % n == i).ToArray()));
```

```python
columns = [letters[i::n] for i in range(n)]
```

Python is ahead on text work. Slicing with a step, `translate` and `Counter` make the
cryptanalysis read like the maths. C# is ahead on the naive version: its JIT makes the
`ord`/`chr` loop fast enough that you'd never need `translate`. In Python the idiomatic way
and the fast way are the same here, but you have to know the builtin exists. Python's `%` is
also friendlier for cyclic arithmetic. In C# you'd write `((x % 26) + 26) % 26`.

## Gotchas

- **`str.isalpha()` is Unicode-wide.** `"é".isalpha()` and `"ł".isalpha()` are both `True`, so
  an `isalpha` filter would let them into a 26-letter cipher, and `ascii_lowercase.index`
  would raise. Test membership in `string.ascii_letters` instead (here a `frozenset`). Also
  filter *before* lowercasing: `"İ".lower()` is two characters long (`i` plus a combining dot).
- **`translate` wants code points, not characters.** `"abc".translate({"a": "b"})` silently
  returns `'abc'`. The dict keys must be `ord("a")`. `str.maketrans` does that conversion for
  you, so always build tables with it.
- **`%` and `//` floor towards negative infinity.** `-3 % 26 == 23` and `-7 // 2 == -4`, while
  C# gives `-3` and `-3`. That is exactly what you want for "shift back by 3", but it bites when
  porting arithmetic that relied on truncation.

## Your turn

1. **Easy: ROT13.** Python ships ROT13 as a codec: `codecs.encode("Hello", "rot13")` gives
   `"Uryyb"`. Add a `cipher rot13` subcommand built on it, and a test that it agrees with
   `caesar(text, 13)` on `data/message.txt`.
2. **Medium: Autokey.** In the autokey variant of Vigenère the key is used once, then the
   plaintext itself continues the key stream. Replace `cycle(...)` with a generator that yields
   the key's shifts and then the shifts of the plaintext letters
   (`itertools.chain(key_shifts(key), …)`). Then run `cipher crack --explain` on an autokey
   ciphertext, and explain in a comment why every key length now looks random.
3. **Stretch: General substitution.** Encrypt `data/message.txt` with a random alphabet:
   `str.maketrans(ascii_lowercase, "".join(random.Random(9).sample(ascii_lowercase, 26)))`.
   Break it by hill climbing. Start from the frequency-order guess, then repeatedly swap two
   letters in the table and keep the swap if a bigram score (a `Counter` over
   `zip(text, text[1:])`) moves closer to English. Add it as another candidate in `crack()`.

## Go deeper

- [`str.translate`](https://docs.python.org/3/library/stdtypes.html#str.translate) and
  [`str.maketrans`](https://docs.python.org/3/library/stdtypes.html#str.maketrans)
- [`itertools.cycle`](https://docs.python.org/3/library/itertools.html#itertools.cycle) and
  [`zip(strict=True)`](https://docs.python.org/3/library/functions.html#zip)
- [`collections.Counter`](https://docs.python.org/3/library/collections.html#collections.Counter)
- [`functools.cache`](https://docs.python.org/3/library/functools.html#functools.cache)
- [Common sequence operations](https://docs.python.org/3/library/stdtypes.html#common-sequence-operations), slicing with a step
- [Text transforms in `codecs`](https://docs.python.org/3/library/codecs.html#text-transforms), which include rot13
- [Index of coincidence](https://en.wikipedia.org/wiki/Index_of_coincidence) and
  [Kasiski examination](https://en.wikipedia.org/wiki/Kasiski_examination), the classic
  alternative to today's approach
- Local lessons: lesson 06, iterators and generators (`cycle`, `next`, generator functions),
  and lesson 02, collections and comprehensions (`Counter`, slicing).
