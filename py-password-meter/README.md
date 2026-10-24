# Day 003 · Password Generator & Strength Meter

`pw` generates passwords and passphrases from the OS's secure random source, and its strength
meter reads a password the way a cracker would, not the way a "must contain a symbol" form does.

## Run it

```bash
cd py-password-meter
uv run pw gen                              # 20 chars, every character class
uv run pw gen -n 16 --no-symbols --unambiguous -c 3
uv run pw phrase                           # 6 EFF words, ~77.5 bits
uv run pw phrase -w 4 --capitalize --number -s ' '
uv run pw check 'P@ssw0rd2024!'            # full breakdown of one password
uv run pw check -f data/passwords.txt      # a table for many
uv run pw check                            # type one at a hidden prompt (no shell history)
uv run pytest
```

## What it looks like

```text
$ uv run pw gen
MF+@@34y<i5Q"i|8=*!8
# 130.9 bits of entropy: 20 chars, 94-symbol alphabet, every class present
$ uv run pw gen -n 16 --no-symbols --unambiguous -c 3
6bReEA6bQQ2fqGv6
nzYSjXaCr7nscLgA
BTutfDWLiirkH93B
# 92.8 bits of entropy: 16 chars, 56-symbol alphabet, every class present
$ uv run pw phrase
riverbed-sevenfold-outclass-fascism-helmet-mantra
# 77.5 bits of entropy: 6 words from a 7,776-word list
$ uv run pw phrase -w 4 --capitalize --number -s ' '
Little Crucial Flatten Plaster9
# 57.0 bits of entropy: 4 words from a 7,776-word list, plus a digit on a random word
```

The password goes to stdout and the `#` line to stderr, so `uv run pw gen | pbcopy` copies only
the password.

Now the meter. This is a password that the "8+ chars, upper, lower, digit, symbol" rule loves:

```text
$ uv run pw check 'P@ssw0rd2024!'
P@ssw0rd2024!
  rating     █░░░░  very weak
  naive       85.4 bits   13 chars, pool of 95
  estimated   13.9 bits   15,200 guesses

  how a cracker sees it
    P@ssw0rd  dictionary                8  common password #1 'password', capitalised, l33t
    2024      year                     20  a year
    !         bruteforce               95  1 random char from a pool of 95

  time to crack
    online, throttled (100/hour)  6 days
    online, unthrottled (10/s)    25 minutes
    offline, slow hash (10k/s)    2 seconds
    offline, fast hash (10B/s)    under a second

  tip: Common passwords and words go first; capitals and l33t swaps barely help.
  tip: Years are among the first things a cracker appends.
  tip: Try 'pw phrase': six random words are ~77 bits and easy to type.
```

That's the standout: **85 bits naive, 14 bits real.** The naive formula (`length × log2(pool)`)
assumes each of the 13 characters was picked at random. A cracker instead tries `password` with
a capital and two l33t swaps (8 guesses), then a recent year (20), then one symbol (95). That's
8 × 20 × 95 = 15,200 guesses in total.

```text
$ uv run pw check -f data/passwords.txt
password                                     naive  estimate  rating       fast-hash crack
password1                                     46.5       5.2  very weak    under a second
P@ssw0rd2024!                                 85.4      13.9  very weak    under a second
Summer2026!                                   72.3      18.2  very weak    under a second
iloveyou2010                                  62.0      11.0  very weak    under a second
qwerty123456                                  62.0       3.3  very weak    under a second
1qaz2wsx                                      41.4       9.4  very weak    under a second
abcabcabcabc                                  56.4       5.6  very weak    under a second
Tr0ub4dor&3                                   72.3      72.3  strong       18 thousand years
correct horse battery staple                 164.7      49.9  fair         1 day
kT9#vQ2$wL7!pX4&                             105.1     105.1  very strong  longer than the universe has existed
ozone-spinach-blurt-mascot-unpaved-rearview  253.0      79.9  strong       4 million years
```

Two rows deserve a second look. The truly random `kT9#…` gets full credit, because there's no
pattern to find. The six-word passphrase scores 79.9 bits, and its true entropy is 77.5 bits
(6 × log2 7776). The meter gets within a few bits of the generator's number, because it reads
the passphrase the way an attacker who knows the EFF list would:

```text
$ uv run pw check ozone-spinach-blurt-mascot-unpaved-rearview
  ...
  estimated   79.9 bits   1,105,369,598,603,666,789,498,880 guesses

  how a cracker sees it
    ozone     dictionary            7,776  word (one of 7,776) 'ozone'
    -         separator                 5  a common separator
    spinach   dictionary            7,776  word (one of 7,776) 'spinach'
    -         separator                 1  a common separator
    ...
```

The extra 2.3 bits are log2(5): the meter has to guess which of five common separators was used.
`Tr0ub4dor&3` is the meter's honest failure. See Gotchas.

## What you'll learn

- **`secrets`, not `random`**: `secrets.choice` and `secrets.randbelow` read the OS CSPRNG,
  with rejection sampling to keep every valid password equally likely
  ([generate.py#L49](src/py_password_meter/generate.py#L49)).
- **Integers that never overflow**: exact inclusion-exclusion counts like `94**20`, and guess
  counts multiplied across segments, with no `BigInteger` in sight
  ([generate.py#L57](src/py_password_meter/generate.py#L57),
  [strength.py#L94](src/py_password_meter/strength.py#L94)).
- **Matchers as generator functions**: each pattern finder is a plain `def` that `yield`s
  matches, with no interface and no class hierarchy
  ([matchers.py#L33](src/py_password_meter/matchers.py#L33)).
- **`re` beyond the basics**: named groups, a backreference for repeats, and a lookahead that
  makes `finditer` return overlapping matches
  ([matchers.py#L77](src/py_password_meter/matchers.py#L77),
  [strength.py#L126](src/py_password_meter/strength.py#L126)).
- **`string` and `str.maketrans`**: ready-made character classes and a one-line l33t decoder
  ([generate.py#L15](src/py_password_meter/generate.py#L15),
  [matchers.py#L29](src/py_password_meter/matchers.py#L29)).
- **`math.log2`, `bisect` and `itertools`**: bits from big integers, thresholds as a lookup
  table, and `groupby(pairwise(...))` for runs
  ([strength.py#L59](src/py_password_meter/strength.py#L59),
  [matchers.py#L97](src/py_password_meter/matchers.py#L97)).

## Code tour

### 1. `secrets` and rejection sampling

```python
pools = [
    "".join(c for c in CLASSES[name] if not (unambiguous and c in AMBIGUOUS)) for name in classes
]
alphabet = "".join(pools)

while True:
    text = "".join(secrets.choice(alphabet) for _ in range(length))
    if all(not set(pool).isdisjoint(text) for pool in pools):
        break
```

`CLASSES` is built from the `string` module's constants (`ascii_lowercase`, `digits`,
`punctuation`), so there are no hand-typed alphabets with a missing character.

Python has two random APIs, and picking the wrong one is a real security bug. `random` is a
Mersenne Twister: fast and seedable, and predictable once someone has seen 624 of its outputs.
`secrets` wraps `os.urandom`. It's the same split as .NET's `Random` vs
`RandomNumberGenerator`, or JS's `Math.random` vs `crypto.getRandomValues`.

"At least one of each class" is the usual requirement. The common implementation (pick one from
each class, fill the rest, shuffle) quietly skews the distribution. Rejection sampling instead
draws a fully uniform string and starts again if a class is missing, so every valid password
stays equally likely. At length 20 only 11% of draws are rejected. Even at length 8, where about
half are, it costs a couple of extra draws.

`while True: ... break` is how you write a `do…while`, which Python doesn't have.

### 2. Exact entropy, because ints are unbounded

```python
def count_valid(length: int, sizes: list[int]) -> int:
    total = sum(sizes)
    return sum(
        (-1) ** k * (total - sum(missing)) ** length
        for k in range(len(sizes) + 1)
        for missing in combinations(sizes, k)
    )
```

Because of the "every class present" rule, the entropy isn't `20 × log2(94)`. It's the log of
the number of strings that pass the rule. Inclusion-exclusion counts them: all strings, minus
the ones missing each class, plus the ones missing each pair, and so on. `combinations(sizes, k)`
yields every k-subset of classes.

`94 ** 20` has 40 digits. Python's `int` is arbitrary-precision by default, so this is exact,
and `math.log2` accepts it directly. There's no `BigInteger` type to opt into (C#) and no `n`
suffix (TS `BigInt`): it's the same `int` you count loops with. A test checks the formula
against brute-force enumeration with `itertools.product`.

### 3. Matchers are generators

```python
def dictionary(password: str) -> Iterator[Match]:
    ranks, common = word_ranks(), password_ranks()
    lower = password.lower()
    for start in range(len(password)):
        for end in range(start + _MIN_WORD, min(len(password), start + _MAX_WORD) + 1):
            token, word = password[start:end], lower[start:end]
            for candidate, how, extra in _spellings(word):
                if (rank := ranks.get(candidate)) is None:
                    continue
                ...
                yield Match(start, end, token, "dictionary", rank * variations * extra, notes)
```

Each matcher (`dictionary`, `sequence`, `keyboard`, `year`, `separator`, `repeat`) is a function
that yields `Match` objects, and the registry is just a tuple of functions:

```python
MATCHERS: tuple[Callable[[str], Iterator[Match]], ...] = (dictionary, sequence, ...)
```

In C# this would be an `IPatternMatcher` interface and six classes. In Python a function already
*is* the single-method object.

`_spellings` is a generator too. It yields the word as typed, un-l33ted and reversed, each with
the extra guesses that variation costs. Un-l33ting is `word.translate(_LEET)`, with a table
built once by `str.maketrans("4@31!|0$57+", "aaeiiiosstt")`. The walrus `:=` binds `rank` and
tests it in one expression.

The wordlists ship *inside* the package. They're read with `importlib.resources.files(...)`
behind `@functools.cache`, so they load once, on first use (the same pattern as day 001).

### 4. Regex tricks: overlapping matches and backreferences

```python
_YEAR = re.compile(r"(?=(?P<year>19\d\d|20\d\d))")
_REPEAT = re.compile(r"(?P<unit>.+?)(?P=unit)+", re.DOTALL)
```

`finditer` never returns overlapping matches: it resumes *after* each one. Wrapping the pattern
in a lookahead `(?=...)` makes the match zero-width, so the scan advances one character at a
time and `'19992000'` yields both `1999` and `2000`. The capture group inside still captures the
text, and `m["year"]` reads it (match objects support `[]` for groups).

`(?P=unit)` is a named backreference: "the same text that `unit` matched". So `abcabcabcabc` is
`abc` four times. The repeat matcher then calls `estimate("abc")` recursively, finds an
ascending sequence (12 guesses), and charges 12 × 4 = 48. This one recursive matcher lives in
`strength.py`, next to `estimate`, to avoid a circular import.

Sequences don't need a regex at all:

```python
for step, run in groupby(pairwise(password), key=lambda pair: ord(pair[1]) - ord(pair[0])):
```

`pairwise('abcx')` gives `ab, bc, cx`. `groupby` collapses consecutive pairs with the same step
(1, 1, 22), so any run with a step of ±1 is an alphabetic or numeric sequence.

### 5. The cheapest way to read the password

```python
best: list[tuple[int, tuple[Match, ...]]] = [(1, ())]
for end in range(1, len(password) + 1):
    options = [(best[m.start][0] * m.guesses, (*best[m.start][1], m)) for m in ending_at[end]]
    guesses, segments = best[end - 1]
    char = Match(end - 1, end, password[end - 1], "bruteforce", pool, "")
    options.append((guesses * pool, (*segments, char)))
    best.append(min(options, key=itemgetter(0)))
```

Matchers report overlapping candidates: `qwerty` is both a keyboard walk and common password #5.
A shortest-path search over positions picks the cheapest cover. `best[i]` is the fewest guesses
needed to produce the first `i` characters. To reach `i`, you either end a match there or
brute-force one more character for `pool` guesses. This is the simplified heart of Dropbox's
zxcvbn.

Brute-forcing every character is always one of the options, so the estimate can never exceed
the naive formula, and a test asserts that for every sample. `(*segments, char)` unpacks into a
new tuple, and `min(..., key=itemgetter(0))` is LINQ's `MinBy(x => x.Item1)`.

Presentation is table-driven too. The rating is `bisect(_RATING_BITS, self.bits)`, which
returns how many thresholds the value has passed: a binary search instead of an `if/elif`
ladder.

## If you wrote this in C# / TypeScript

| Task | C# | TypeScript | Python |
| --- | --- | --- | --- |
| Secure random choice | `RandomNumberGenerator.GetInt32(n)` | `crypto.getRandomValues` + your own bias check | `secrets.choice(seq)` |
| Fast, insecure random | `Random.Shared` | `Math.random()` | `random` module |
| Huge exact integers | `System.Numerics.BigInteger` | `BigInt` (`10n`, can't mix with `number`) | plain `int` |
| log2 of a 40-digit int | `BigInteger.Log(x, 2)` | convert to `number`, lose precision | `math.log2(x)` |
| Character classes | hand-written strings | hand-written strings | `string.ascii_letters`, `digits`, `punctuation` |
| Overlapping regex matches | lookahead + `Matches` | lookahead + `matchAll` | lookahead + `finditer` |
| Read a password silently | `Console.ReadKey(intercept: true)` loop | `readline` with muted output | `getpass.getpass()` |
| Pluggable matchers | `IMatcher` + classes | array of functions | tuple of generator functions |

Secure random choice in each language:

```csharp
// C#: GetInt32 is unbiased; the old "GetBytes, then % n" pattern is not
var password = string.Concat(Enumerable.Range(0, length)
    .Select(_ => alphabet[RandomNumberGenerator.GetInt32(alphabet.Length)]));
```

```typescript
// TypeScript: getRandomValues gives raw numbers; avoiding modulo bias is on you
function choice(alphabet: string): string {
  const limit = 2 ** 32 - (2 ** 32 % alphabet.length);
  const buf = new Uint32Array(1);
  do crypto.getRandomValues(buf); while (buf[0] >= limit);
  return alphabet[buf[0] % alphabet.length];
}
```

```python
text = "".join(secrets.choice(alphabet) for _ in range(length))
```

C# is on par here (`GetInt32` arrived in .NET Core 3.0). In the browser you write the rejection
loop yourself, and getting `% n` wrong is a classic bias bug. Python's real advantage is its
integers: the entropy maths in `count_valid` is a few lines, where in TypeScript you'd juggle
`BigInt` and `number` and have no `log2` for `BigInt` at all. What Python lacks is a built-in
password-hashing API like ASP.NET Identity's `PasswordHasher`. To store passwords, reach for
`hashlib.scrypt` or the `argon2-cffi` package.

## Gotchas

- **A meter only knows what's in its dictionaries.** `Tr0ub4dor&3` scores 72 bits here because
  "troubador" is in neither the EFF list nor the top 10k passwords. With a full English
  dictionary, zxcvbn rates it about 28 bits (the famous xkcd 936 number). Don't read a high score
  as proof of strength; a *low* score, though, is proof of weakness. The dictionaries cut the
  other way too: `correct horse battery staple` scores 49.9 bits, below four random EFF words
  (54 bits), because `horse` and `battery` are common passwords #648 and #5,326.
- **Entropy belongs to the process, not the string.** `pw phrase` reports 77.5 bits because it
  *knows* it picked 6 of 7,776 words uniformly. The same string chosen by a person who picked
  their favourite words has far less. Likewise, `--capitalize` adds 0 bits: a rule the attacker
  knows isn't a secret.
- **Passwords in argv end up in your shell history**, and they show in `ps` while the command
  runs. `pw check 'real-password'` is fine for the demo. For a password you actually use, run
  `pw check` with no arguments and type it at the `getpass` prompt, which masks the whole
  report.

## Your turn

1. **Easy:** add a `date` matcher for `DDMMYYYY` and `MMDDYY` tokens (`14021990`, `070388`).
   Use one regex with named groups `(?P<day>…)(?P<month>…)(?P<year>…)` inside a `(?=…)`
   wrapper, and charge `31 × 12 × 100` guesses. Add `iloveyou14021990` to the parametrized
   weak-passwords test.
2. **Medium:** let the meter use any wordlist: `pw check --words /usr/share/dict/words`, where
   each word costs the list's size. Then check that `Tr0ub4dor&3` drops below 40 bits. Hint:
   `word_ranks` is behind `@cache`, so pass the extra words in rather than mutating a global.
3. **Stretch:** a `pw dice` mode for offline passphrases. Read five d6 rolls per word from
   stdin (`43231 12611 …`), look them up via the EFF list's first column, and refuse anything
   that isn't five digits from 1 to 6. Then show that the `secrets` path is uniform: generate
   20,000 one-word phrases, bucket them by the first dice digit, and compute a chi-squared
   statistic with `Counter`.

## Go deeper

- [`secrets`](https://docs.python.org/3/library/secrets.html), including its "recipes and best
  practices" section
- [`re` syntax: lookahead and named groups](https://docs.python.org/3/library/re.html#regular-expression-syntax)
  and [`bisect`](https://docs.python.org/3/library/bisect.html)
- [`itertools`: `pairwise`, `groupby`, `combinations`](https://docs.python.org/3/library/itertools.html)
- [zxcvbn](https://github.com/dropbox/zxcvbn), the realistic strength estimator this meter
  simplifies
- Wordlists: the [EFF long wordlist](https://www.eff.org/dice) (CC BY 3.0 US) and SecLists'
  [10k most common passwords](https://github.com/danielmiessler/SecLists) (MIT), bundled in
  `src/py_password_meter/wordlists/`
- Local lessons: lesson 06 (iterators and generators), lesson 13 (stdlib and ecosystem),
  lesson 05 (type hints).
