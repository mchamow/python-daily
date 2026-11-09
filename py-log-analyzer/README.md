# Day 012 · Log File Analyzer

`logscan` streams access logs (plain, gzip, bzip2, xz, Zstandard or stdin) through a lazy
generator pipeline and reports traffic, error spikes, slow endpoints, top clients and the slowest
requests. It analyzed a million lines in about 28 MiB, the same memory it uses for forty
thousand, and it finds the outage planted in the sample logs without being told where to look.
It uses only the standard library.

## Run it

```bash
cd py-log-analyzer
uv run logscan data/access.log*                       # three rotated files: .zst, .gz and plain
uv run logscan data/access.log* -n 3 \
    --since 2026-11-08T14:00+01:00 --until 2026-11-08T14:30+01:00   # zoom into the outage
uv run loggen -n 1000000 --rate 300 | uv run logscan -              # a million lines, never on disk
uv run pytest
```

`data/` holds three days of a made-up shop's nginx logs, rotated the way logrotate leaves them:
`access.log.2.zst` (Nov 7), `access.log.1.gz` (Nov 8) and today's plain `access.log`, about
39,000 requests in all. `loggen` is the project's second command. It writes an endless,
deterministic stream of realistic log lines: a scraper bot, a vulnerability scanner, a few corrupt
lines, and one outage. From 14:07 to 14:20 on Nov 8 the payment upstream is down, and checkout
returns 503 and 504 while clients retry. `uv run loggen --samples data` rebuilds the sample files
byte for byte.

## What it looks like

```
$ uv run logscan data/access.log*
Window    2026-11-07 00:00 → 2026-11-09 10:59 (+0100)
Requests  39,463  ·  1.8 GiB sent  (15 unparseable lines skipped)
Status    2xx 91.28%   3xx 6.83%   4xx 1.07%   5xx 0.81%
Latency   p50 30 ms   p95 302 ms   p99 821 ms   max 10.9 s

Traffic   ▂▂▁▁▁▁▂▂▃▄▄▅▆▆▇▆▇▆▆▅▅▄▄▃▂▂▁▁▁▁▂▂▃▄▄▅▅▆█▇▇▆▆▅▅▄▃▃▂▂▁▁▁▁▂▂▃▄▄  peak 1,493
5xx            ▁ ▁ ▁▁▁▁ ▁▁▁▁▁▁▁▁▁▁▁ ▁ ▁  ▁   ▁▁▁█▁▁▁▁▁▁▁▁ ▁ ▁    ▁ ▁▁  peak 260
          1 column = 1 h

Incidents (≥5 5xx a minute, ≥5% of traffic): 1
  2026-11-08 14:07 → 14:20  13 min  258/544 failed (47%)  mostly POST /api/checkout (252)

Slowest endpoints by p95 (≥20 hits)
  endpoint                      hits     5xx      p50      p95      p99      max
  POST /api/checkout           1,352   18.7%   290 ms   10.0 s   10.4 s   10.4 s
  GET /reports/export.csv         74    0.0%    2.5 s    5.8 s    9.8 s   10.9 s
  POST /api/orders/{id}/pay      682    1.2%   408 ms    1.1 s    1.7 s   10.3 s
  GET /api/search              3,064    0.2%   162 ms   686 ms    1.3 s    3.0 s
  POST /api/login              1,000    0.0%   116 ms   308 ms   450 ms   727 ms

Top clients
  203.0.113.66       4,637   11.8%
  192.0.2.10         1,265    3.2%
  198.51.100.13        355    0.9%
  ...

Slowest requests
   10.9 s  2026-11-07 23:03:30  200  GET /reports/export.csv  (203.0.113.169)
   10.4 s  2026-11-08 14:13:08  504  POST /api/checkout  (198.51.100.16)
   ...

Unparseable lines (first few)
  data/access.log.1.gz:2612: 198.51.100.217 - - [08/Nov/2026:08:22:56 +0100] "\x16\x03\x01\x02\x00\x01" 400 157 "-" "-…
  ...

39,478 lines in 0.21 s (185k lines/s) · peak memory 30 MiB
```

The incident line is the wow moment. Nothing told `logscan` about 14:07. It counts 5xx per
minute, finds the run of bad minutes and names the endpoint behind most of them. Note also that
`/api/orders/1842/pay` and its siblings are grouped as `/api/orders/{id}/pay`. Zoom in and the
columns become minutes:

```
$ uv run logscan data/access.log* -n 3 --since 2026-11-08T14:00+01:00 --until 2026-11-08T14:30+01:00
Window    2026-11-08 14:00 → 2026-11-08 14:29 (+0100)
Requests  888  ·  30.3 MiB sent  (15 unparseable lines skipped)
Status    2xx 63.63%   3xx 6.31%   4xx 1.01%   5xx 29.05%
Latency   p50 26 ms   p95 10.2 s   p99 10.4 s   max 10.4 s

Traffic   ▂▃▂▃▃▃▃█▆▅▇█▇▆▆▆▆▇▄▆▄▃▂▃▄▃▃▃▃▄  peak 54
5xx              █▅▅▇▇▆▆▆▆▆▇▅▆            peak 26
          1 column = 1 min
...
  POST /api/checkout        292   86.3%    26 ms   10.4 s   10.4 s   10.4 s
```

A p50 of 26 ms next to a p95 of 10.4 s tells the story: most failures were instant 503s from an
open circuit breaker, and the rest were 504s after a 10-second upstream timeout. Traffic jumps at
14:07 because every failed checkout is retried. (The 15 skipped lines are counted across all
lines read, before the time filter.)

And at scale, piped straight from the generator, so the million lines never touch the disk:

```
$ uv run loggen -n 1000000 --rate 300 | uv run logscan - -n 3
Window    2026-11-07 00:00 → 2026-11-09 11:51 (+0100)
Requests  999,566  ·  45.7 GiB sent  (434 unparseable lines skipped)
...
Incidents (≥5 5xx a minute, ≥5% of traffic): 1
  2026-11-08 14:07 → 14:20  13 min  5,860/12,738 failed (46%)  mostly POST /api/checkout (5,760)
...
1,000,000 lines in 27.75 s (36k lines/s) · peak memory 26 MiB
```

Here the pipe runs at the speed of `loggen`, the slower of the two. These are measurements on the
same million lines saved as a 170 MB file, on a busy laptop (load average 13, so treat the times
as rough):

| How the file is read | Peak memory | Time |
| --- | --- | --- |
| `logscan big.log` (streaming) | **28 MiB** | 4.8–7.8 s |
| `open(p).readlines()`, and nothing else | 244 MiB | 0.3 s |
| `list(parse(read_lines([p])))`, a list of `Request`s | 507 MiB | 3.6 s |

Memory scales with the number of distinct IPs, endpoints and minutes. It doesn't scale with the
number of lines.

## What you'll learn

- **Generator pipelines as LINQ's deferred execution**, with one big difference: a Python
  generator can be iterated only *once*. That's why every aggregate is folded in a single pass
  ([__init__.py#L43](src/py_log_analyzer/__init__.py#L43),
  [stats.py#L108](src/py_log_analyzer/stats.py#L108)).
- **Reading compressed files lazily** with Python 3.14's `compression` package, including the new
  stdlib `compression.zstd`. The format is chosen by a `match` on the sniffed magic bytes
  ([source.py#L39](src/py_log_analyzer/source.py#L39)).
- **Regex performance**: the "unrolled loop" form of a quoted string with escapes made the whole
  run 3× faster, and `re.VERBOSE | re.ASCII` keeps a 10-group pattern readable and exact
  ([parse.py#L17](src/py_log_analyzer/parse.py#L17)).
- **`lru_cache` on the hot path**: timestamps are parsed once a minute instead of once a line,
  15× faster than `strptime` ([parse.py#L81](src/py_log_analyzer/parse.py#L81)).
- **Streaming top-N with `heapq`** and **streaming percentiles with a log-bucketed `Counter`**,
  both in constant memory ([stats.py#L67](src/py_log_analyzer/stats.py#L67),
  [sketch.py#L15](src/py_log_analyzer/sketch.py#L15)).
- **Small things that add up**: `Counter` addition, `itertools.batched` (3.12+), `takewhile` +
  `groupby` to split one stream into daily files
  ([generate.py](src/py_log_analyzer/generate.py)), and PEP 758's `except A, B:` without
  parentheses (3.14).

## Code tour

### 1. The pipeline: nothing happens until someone asks

```python
def read_lines(sources: Iterable[str]) -> Iterator[Line]:
    for source in sources:
        with _open(source) as stream:
            for number, text in enumerate(stream, start=1):
                yield Line(source, number, text)


def parse(lines: Iterable[Line], intake: Intake) -> Iterator[Request]:
    for line in lines:
        intake.lines += 1
        if (request := parse_line(line.text)) is None:
            intake.reject(line)
        else:
            yield request


def pipeline(files, intake, since, until) -> Iterator[Request]:
    requests = parse(read_lines(files), intake)
    if since is not None:
        requests = (r for r in requests if r.time >= since)
    if until is not None:
        requests = (r for r in requests if r.time < until)
    return requests
```

`pipeline()` returns immediately, before a single file is opened. Each stage is a generator that
wraps the previous one, so exactly one line is in flight at a time. `analyze` pulls a request,
the filter pulls from `parse`, `parse` pulls from `read_lines`, and `read_lines` pulls one line
from the decompressor. This is `IEnumerable<T>` with `yield return` and `.Where()`. Day 006
introduced the shape; today it's what makes 1 GB and 1 MB cost the same memory.

The conditional filters use a pattern LINQ users know: rebinding `requests` to a new generator
expression that wraps the old one (`query = query.Where(...)`). A file object is itself a lazy
iterator of lines, so `for text in stream` never reads the whole file. `read_lines` keeps only one
file open at a time and closes each one as soon as it's done.

`Intake` is how a lazy stage reports on itself. `parse` can't return a count, because the caller
gets a generator rather than a result, so it updates an object the caller owns. A test makes the
laziness visible: right after `parse(...)` is called, `intake.lines` is still 0.

### 2. One pass, many answers

```python
def add(self, r: Request) -> None:
    self.requests += 1
    ...
    self.statuses[r.status] += 1
    self.ips[r.ip] += 1

    name = r.endpoint
    ep = self.endpoints[name]  # defaultdict(Endpoint)
    minute = self.minutes[r.time.replace(second=0)]  # defaultdict(Minute)
    ...
    if r.ms is not None:
        ep.latency.add(r.ms)
        entry = (r.ms, self.requests, r)
        if len(self._slowest) < self.top:
            heapq.heappush(self._slowest, entry)
        elif r.ms > self._slowest[0][0]:
            heapq.heapreplace(self._slowest, entry)
```

This is where Python and LINQ really part ways. In C# you'd write `logs.GroupBy(r => r.Ip)`,
then `logs.OrderByDescending(r => r.Ms).Take(5)`, then a third query. Each one re-enumerates
`logs`, which here means re-reading and re-decompressing the file: a lazy `IEnumerable` can be
run again, and you pay for it silently. A Python generator is spent after one pass, and a second
`for` loop silently gets nothing. So the analyzer is a fold, LINQ's `Aggregate`, with one
accumulator that holds every answer.

Each aggregate grows with what it counts, not with the number of lines: `Counter`s for statuses
and IPs, `defaultdict(Endpoint)` keyed by normalised endpoint, one `Minute` per minute of log
time, and a heap of size `top`. `heapq.nlargest(5, requests)` (Day 007) runs this same
algorithm, but it consumes the iterator itself, which a single shared pass can't allow. So the
heap is kept by hand. It's a min-heap whose root is the fastest of the five slowest, and
`heapreplace` swaps that out when something slower arrives. The middle element of the tuple is a
tie-breaker; Gotchas explains why it has to be there.

### 3. Percentiles without keeping the values

```python
def add(self, value: float) -> None:
    self.count += 1
    if value <= 0:
        self.zeros += 1
        return
    self.max = max(self.max, value)
    self._buckets[math.ceil(math.log(value) / self._log_gamma)] += 1


def quantile(self, q: float) -> float:
    rank = round(q * (self.count - 1))
    seen = self.zeros
    ...
    for k in sorted(self._buckets):
        seen += self._buckets[k]
        if rank < seen:
            return min(2 * self._gamma**k / (self._gamma + 1), self.max)
```

An exact p99 means keeping every value: that's the 507 MiB row in the table above. Instead the
sketch keeps a `Counter[int]` of buckets whose bounds grow geometrically, by
`gamma = 1.01 / 0.99`. Bucket `k` covers `(gamma**(k-1), gamma**k]`, and answering with its
midpoint is at most 1% off *relative to the value*: ±3 ms at 300 ms, ±0.1 s at 10 s. That's the
kind of error you want for latencies. Everything from 1 ms to 10 minutes fits in about 660
buckets. The tests check this against exact nearest-rank quantiles of 50,000 log-normal values for
q from 0 to 1, and check that 200,000 values use no more buckets than 50,000.

This is the idea behind DDSketch (Datadog), and close to what Prometheus native histograms do.
`Counter` does quiet work here too: a missing key reads as 0, so `+= 1` needs no setup.

### 4. The regex: readable, exact and fast

```python
LINE = re.compile(
    r"""
    (?P<ip>\S+) \s \S+ \s \S+ \s                          # client, identd, user
    \[ (?P<minute>\d\d/\w{3}/\d{4}:\d\d:\d\d)             # 08/Nov/2026:14:07
       :(?P<second>\d\d) \s (?P<offset>[+-]\d{4}) \] \s   # :12 +0100
    "(?P<method>[A-Z]+) \s (?P<path>\S+) \s HTTP/[\d.]+" \s
    (?P<status>\d{3}) \s (?P<size>\d+|-)
    (?: \s "[^"\\]*(?:\\.[^"\\]*)*"                       # referer
        \s "(?P<agent>[^"\\]*(?:\\.[^"\\]*)*)" )?         # user agent
    (?: \s (?P<seconds>\d+(?:\.\d+)?) )?                  # nginx $request_time
    \s*$
    """,
    re.VERBOSE | re.ASCII,
)
```

Three choices here are worth stealing:

- **`re.ASCII`** makes `\d` mean `[0-9]` and `\w` mean `[A-Za-z0-9_]` for the whole pattern, so
  you don't have to spell out `[0-9]` everywhere as Day 011 did.
- **Optional tails**, `(?: … )?`, let one pattern read Apache's common format, the combined format
  and nginx with `$request_time`. Without a time, the report just leaves out the latency
  sections.
- **The unrolled loop.** A quoted string that may contain `\"` is usually written
  `"(?:[^"\\]|\\.)*"`, which tries an alternation once *per character*. Rewritten as
  `[^"\\]*(?:\\.[^"\\]*)*` ("a run of ordinary characters, then any number of escape-plus-run"),
  the engine consumes whole runs at once. On these lines, with ~100-character user agents,
  matching went from **5.8 µs to 1.3 µs** per line, and the million-line run went from 15.3 s to
  4.8 s. The profiler found it: `cProfile` put `Pattern.match` at 10 of the 24 seconds.

The minute and the second are captured separately because of the next trick.

### 5. Parse each minute once, not each line

```python
@lru_cache(maxsize=2048)
def _minute(stamp: str, offset: str) -> datetime:
    day, month, rest = stamp.split("/")
    year, hour, minute = rest.split(":")
    sign = -1 if offset[0] == "-" else 1
    tz = timezone(sign * timedelta(hours=int(offset[1:3]), minutes=int(offset[3:5])))
    return datetime(int(year), _MONTH_NUMBER[month], int(day), int(hour), int(minute), tzinfo=tz)


def parse_line(text: str) -> Request | None:
    ...
    try:
        time = _minute(m["minute"], m["offset"]).replace(second=int(m["second"]))
    except KeyError, ValueError:  # "Foo" as a month, 31/Feb, a +2500 offset
        return None
```

A busy log has hundreds of lines per minute, and they all share the same
`"08/Nov/2026:14:07"` + `"+0100"`. Caching on that pair and adding the seconds with `.replace()`
took **0.32 µs**, against **4.73 µs** for `datetime.strptime(s, "%d/%b/%Y:%H:%M:%S %z")`. That's
15× faster, or about 4.4 s saved per million lines, and the cache misses only once a minute.
`.replace()` returns a new datetime. Datetimes are immutable, which is also why it's safe for the
cache to hand the same object to every caller.

The month comes from a hand-written dict, not `%b`, because `%b` follows the process locale (see
Gotchas). And `except KeyError, ValueError:` without parentheses is new in Python 3.14
(PEP 758). It's allowed only when there's no `as`, and it means the same as the tuple form.

## If you wrote this in C# / TypeScript

| Task | C# (.NET) | TypeScript (Node) | Python |
| --- | --- | --- | --- |
| Lazy sequence | `IEnumerable<T>` + `yield return` | generator `function*` | generator function or expression |
| Iterate it a second time | runs the query again (re-reads the file) | a used generator yields nothing | a used generator yields nothing |
| Filter / project | `.Where()` / `.Select()` | `.filter()`/`.map()` (eager on arrays), iterator helpers | `(r for r in rs if …)`, `map`, `filter` |
| Fold | `.Aggregate(seed, fn)` | `.reduce()` | a `for` loop into an accumulator (`functools.reduce` exists) |
| Read lines lazily | `File.ReadLines(path)` | `readline.createInterface({ input })` (async) | `for line in open(path)` |
| Read a `.gz` | `GZipStream` + `StreamReader` | `createReadStream().pipe(zlib.createGunzip())` | `gzip.open(path, "rt")` |
| Zstandard | `ZstdSharp` (NuGet) | `zlib.createZstdDecompress()` (Node 22.15+) | `compression.zstd` (3.14 stdlib) |
| Top-N while streaming | `PriorityQueue<T, TPriority>` | hand-rolled heap or a library | `heapq` on a plain `list` |
| Memoise | `ConcurrentDictionary.GetOrAdd`, `IMemoryCache` | a `Map` by hand | `@functools.lru_cache` |
| Count by key | `.GroupBy(x).ToDictionary(g => g.Key, g => g.Count())` | `Map` + loop, `Object.groupBy` | `Counter(…)`, `.most_common(n)` |

The same filter-then-fold, side by side:

```csharp
var stats = File.ReadLines(path)
    .Select(ParseLine).Where(r => r is not null && r.Time >= since)
    .Aggregate(new Stats(), (s, r) => { s.Add(r!); return s; });
```

```python
requests = (r for r in parse(read_lines([path]), intake) if r.time >= since)
stats = analyze(requests)  # a for loop calling stats.add(r)
```

Python is simpler in two ways here. Decompression, Zstandard included, is one stdlib call that
returns an ordinary line iterator. And `Counter`, `defaultdict` and `heapq` are all built in.

It's harder in two ways too. Nobody actually uses a fold function: `reduce` exists, but a plain
loop is considered clearer. And the one-shot generator turns LINQ's performance trap (a hidden
second enumeration) into a correctness trap (a hidden *empty* enumeration). Raw speed is the
other cost: about 200k lines/s on one core, where a C# version would comfortably do several
million. When that matters, the usual Python answer is to split the files across processes (Day 016
uses `concurrent.futures`).

## Gotchas

- **A generator is used up after one pass, silently.** `top_ips = Counter(r.ip for r in requests)`
  followed by `heapq.nlargest(5, requests, key=…)` gives an empty list, with no error. If you need
  two passes, fold once (as here), materialise with `list()` and pay for the memory, or call the
  function that *makes* the generator a second time. `itertools.tee` looks like the fix, but it
  buffers everything one consumer has seen and the other hasn't. If one consumer runs to the end
  first, that's the whole log.
- **Log files aren't UTF-8 until proven otherwise.** User agents and paths carry whatever bytes
  clients send. `open(path)` with the default `errors="strict"` raises `UnicodeDecodeError`
  partway through a 2 GB file. That happened during the benchmark for this lesson, on the one
  planted `0xff` byte. `errors="backslashreplace"` keeps the line and shows the byte as `\xff`.
  Also, `strptime`'s `%b` and `%a` follow the locale: once any code calls
  `locale.setlocale(locale.LC_ALL, "")`, a Polish locale expects `lis`, not `Nov`. Log formats
  are always English, so map month names yourself.
- **`heapq` compares whole tuples.** With `(ms, request)` entries, two requests with the same `ms`
  fall through to comparing the `Request` objects, and a dataclass without `order=True` raises
  `TypeError: '<' not supported`. It only happens once two timings tie, which makes it easy to
  miss. Put a unique counter in the middle: `(ms, seq, request)`. A test feeds in three 50 ms
  requests to make sure.

## Your turn

1. **Easy:** add `--status` (accepting `504`, `5xx` or `4xx`) as one more generator stage in
   `pipeline()`. Turn the flag into a predicate with `match` (`case [d, "x", "x"]` on
   `list(text)` is one way). Then check that `uv run logscan data/access.log* --status 504` lists
   only checkout timeouts under "Slowest requests".
2. **Medium:** add `--json` so the report can feed a dashboard or `jq`. Give `Stats` and
   `Incident` an `as_dict()` (or use `dataclasses.asdict` where it fits), serialise datetimes
   with `.isoformat()`, and keep the text report as the default. Write a test that parses the
   output with `json.loads` and finds the 14:07 incident.
3. **Stretch:** add `--follow`, like `tail -f`. Write a generator that, on reaching the end of
   the last file, sleeps 0.5 s and then yields any new lines, forever. The stream never ends, so
   print a fresh report every N seconds from inside `analyze`'s loop. Handle rotation too: when
   the file's inode changes or it shrinks, reopen it. Test it with `tmp_path`, a writer thread
   and a stop event.

## Go deeper

- [Generators](https://docs.python.org/3/howto/functional.html#generators), in the functional
  programming HOWTO
- [`compression`](https://docs.python.org/3/library/compression.html) and
  [`compression.zstd`](https://docs.python.org/3/library/compression.zstd.html), new in 3.14
- [`heapq`](https://docs.python.org/3/library/heapq.html),
  [`collections.Counter`](https://docs.python.org/3/library/collections.html#collections.Counter),
  [`itertools.batched`](https://docs.python.org/3/library/itertools.html#itertools.batched)
- [`functools.lru_cache`](https://docs.python.org/3/library/functools.html#functools.lru_cache)
  and [`cProfile`](https://docs.python.org/3/library/profile.html), which found the slow regex
- [Codec error handlers](https://docs.python.org/3/library/codecs.html#error-handlers)
  (`backslashreplace`, `surrogateescape`)
- [PEP 758](https://peps.python.org/pep-0758/): `except` and `except*` without brackets
- [DDSketch](https://arxiv.org/abs/1908.10693), the paper behind `sketch.py`
- David Beazley's [Generator Tricks for Systems Programmers](https://www.dabeaz.com/generators/),
  the classic talk on exactly this kind of pipeline
- Local lessons: lesson 06 (iterators and generators) and lesson 13 (stdlib and ecosystem)
