# 100 Days of Python: progress

Run `/python-daily` in Claude Code to build the next day. See
[CURRICULUM.md](CURRICULUM.md) for the full plan.

| Day | Date | App | Highlights |
| --- | ---- | --- | ---------- |
| 001 | 2026-10-19 | [Word Frequency Counter](py-word-frequency/README.md) | Counter algebra, generators, argparse, pathlib rglob, casefold & Unicode regex, importlib.resources |
| 002 | 2026-10-22 | [Unit Converter REPL](py-unit-converter/README.md) | match list & class patterns, assert_never exhaustiveness, Fraction exact maths, Decimal contexts & Inexact flag, dict dispatch + difflib, input() REPL |
| 003 | 2026-10-24 | [Password Generator & Strength Meter](py-password-meter/README.md) | secrets vs random, rejection sampling, unbounded int entropy maths, generator-function matchers, regex lookahead & backreferences, bisect/groupby/pairwise |
| 004 | 2026-10-25 | [Todo CLI with JSON Storage](py-todo-cli/README.md) | dataclasses + StrEnum, type-hint-driven JSON decoder, atomic writes (tempfile + os.replace), flock + @contextmanager transactions, argparse subparsers & parents, match guards |
| 005 | 2026-10-26 | [Expense Splitter](py-expense-splitter/README.md) | Decimal largest-remainder allocation, match mapping patterns, defaultdict(dataclass), min/max/sorted key=, greedy vs bitmask-DP optimal settle-up, PEP 695/696 constrained generics |
| 006 | 2026-10-27 | [Markdown TOC Generator](py-md-toc/README.md) | named groups + lastgroup + re.sub callbacks, re.VERBOSE, lazy generator pipeline, GitHub-exact slugs with dedupe, match on dataclass sequences, newline-preserving atomic rewrite |
| 007 | 2026-10-28 | [Disk Usage Explorer](py-disk-usage/README.md) | custom `__format__` presentation types, int-subclass traps, recursive os.scandir + DirEntry, os.walk pruning with dirnames[:], yield from + heapq.nlargest streaming, du-exact st_blocks & hard-link dedupe |
| 008 | 2026-10-31 | [Terminal Quiz Game](py-terminal-quiz/README.md) | csv newline=""/utf-8-sig/Sniffer/restkey/line_num, ExceptionGroup + except*, seeded random.Random replays & str seeds, perf_counter behind an injectable clock, NFKD + casefold + SequenceMatcher answer matching, asdict/Entry(**d) JSON high scores |
| 009 | 2026-11-02 | [Cipher Toolkit](py-cipher-toolkit/README.md) | str.maketrans/translate (138× an ord/chr loop), @cache shift tables, itertools.cycle key stream, letters[i::n] columns + index of coincidence, Counter chi-squared cracking, zip(strict=True) & Literal match |
| 010 | 2026-11-03 | [Habit Tracker with Streaks](py-habit-tracker/README.md) | date.toordinal() + divmod period numbering, groupby value-minus-index streaks, calendar.Calendar.monthdatescalendar & firstweekday, 24-bit ANSI SGR + NO_COLOR/isatty + visible-width padding, match on str.split() line parser, OnDays \| PerWeek dataclass union |
| 011 | 2026-11-04 | [CSV → SQLite Importer](py-csv-sqlite/README.md) | regex + fromisoformat type inference lattice (frozenset-keyed widen), STRICT tables + CHECK constraints, autocommit=False transactional DDL, executemany from a generator with failing-line tracking, create_function REGEXP, pragma_table_info(?) append checks |
| 012 | 2026-11-09 | [Log File Analyzer](py-log-analyzer/README.md) | lazy generator pipeline + single-pass fold (one-shot generators vs LINQ re-enumeration), compression.zstd/gzip magic-byte sniffing, unrolled-loop regex (4× faster), lru_cache per-minute timestamps (15× strptime), streaming heapq top-N + log-bucketed percentile sketch, per-minute incident detection with batched sparklines |
