# 100 Days of Python: curriculum

One small, complete, working app per day, built by `/python-daily`. Each day lives in
`py-slug/`: a self-contained uv project with its own dependencies, tests and a README. The
README is the lesson. Difficulty rises phase by phase, and later days reuse earlier ideas.

Each line gives the app, then what it **shows** about Python, then the **.NET/TS angle**: what to
compare it with.

## Phase 1: Everyday Python with the standard library (days 1–10)

- **001 · Word Frequency Counter**: top-N words across text files, with stop-word filtering. *Shows:* `Counter`, `pathlib`, comprehensions, `argparse`. *vs:* LINQ `GroupBy/OrderBy` vs `Counter.most_common`.
- **002 · Unit Converter REPL**: an interactive shell (`10 km to mi`). *Shows:* `match` on parsed input, dict dispatch, `Decimal`. *vs:* switch expressions, `Console.ReadLine` loops.
- **003 · Password Generator & Strength Meter**: generates passphrases and scores entropy. *Shows:* `secrets`, `string`, `re`, `math.log2`. *vs:* `RandomNumberGenerator` / `crypto.getRandomValues`.
- **004 · Todo CLI with JSON Storage**: `add/list/done/rm` subcommands. *Shows:* dataclasses ↔ JSON, `argparse` subparsers, atomic file writes. *vs:* System.CommandLine, `System.Text.Json`.
- **005 · Expense Splitter**: who owes whom after a trip, settling with the fewest transfers. *Shows:* `Decimal` money, `defaultdict`, `sorted(key=)`, greedy algorithms. *vs:* `decimal` in C#, JS float pitfalls.
- **006 · Markdown TOC Generator**: injects a table of contents into Markdown files. *Shows:* regex with named groups, generators, slugify, in-place file rewrite. *vs:* `Regex` / `String.prototype.replace`.
- **007 · Disk Usage Explorer**: a `du`-style tree with human-readable sizes. *Shows:* `os.scandir`, recursion vs `os.walk`, generators, `__format__`. *vs:* `DirectoryInfo.EnumerateFiles`, Node `fs.readdir`.
- **008 · Terminal Quiz Game**: questions loaded from CSV, timed answers, high scores. *Shows:* `csv`, `random`, `time.perf_counter`, `json` persistence. *vs:* `Stopwatch`, `performance.now`.
- **009 · Cipher Toolkit**: Caesar, Vigenère and frequency-analysis cracking. *Shows:* `str.translate`/`maketrans`, `itertools.cycle`, `zip`, `Counter`. *vs:* char arithmetic in C#.
- **010 · Habit Tracker with Streaks**: log habits and print a calendar heatmap. *Shows:* `datetime`/`date` arithmetic, the `calendar` module, ANSI colour. *vs:* `DateOnly`, JS `Date` quirks.

## Phase 2: Data in, data out (days 11–20)

- **011 · CSV → SQLite Importer**: infers column types and loads any CSV into SQLite. *Shows:* `csv.DictReader`, `sqlite3`, `executemany`, type inference. *vs:* Dapper / ADO.NET, `better-sqlite3`.
- **012 · Log File Analyzer**: streams huge access logs and reports errors, slow endpoints and top IPs. *Shows:* lazy generator pipelines, regex, `Counter`, `heapq.nlargest`. *vs:* LINQ deferred execution.
- **013 · Personal Library Catalog**: books in SQLite with search and simple migrations. *Shows:* `sqlite3.Row`, context-managed transactions, schema versioning. *vs:* EF migrations.
- **014 · Weather CLI**: forecasts from Open-Meteo (no key) with a disk cache and offline sample. *Shows:* first third-party library (`httpx`), dataclass parsing, caching. *vs:* `HttpClient`, `fetch`.
- **015 · RSS Feed Reader**: aggregates feeds, deduplicates, shows unread items. *Shows:* `xml.etree.ElementTree`, `email.utils` dates, `html` unescaping. *vs:* `XDocument`, DOMParser.
- **016 · Batch Image Thumbnailer**: resizes and watermarks a folder of images in parallel. *Shows:* Pillow, `concurrent.futures`, `pathlib.glob`. *vs:* ImageSharp, `sharp`.
- **017 · PDF Invoice Generator**: invoices from a TOML file, rendered to PDF. *Shows:* `tomllib`, `fpdf2`, `Decimal` formatting. *vs:* QuestPDF, pdfkit.
- **018 · Excel Report Builder**: an XLSX with formulas, styling and a chart. *Shows:* `openpyxl`, data shaping with comprehensions. *vs:* ClosedXML / EPPlus, SheetJS.
- **019 · Layered Config Loader**: defaults → TOML file → env vars → CLI flags, with provenance. *Shows:* `ChainMap`, `tomllib`, `os.environ`, dataclass validation. *vs:* `IConfiguration` providers.
- **020 · Duplicate File Finder**: finds duplicates by size, then hash, with a safe dry run. *Shows:* `hashlib`, chunked reads, `defaultdict(list)`, `shutil`. *vs:* `SHA256.HashData`, streams.

## Phase 3: Modelling with Python's object system (days 21–30)

- **021 · Bank Ledger**: accounts, transfers and statements with invariants enforced. *Shows:* frozen dataclasses, custom exceptions, `__str__` vs `__repr__`. *vs:* records, domain exceptions.
- **022 · Vector & Matrix Library**: a small linear-algebra library with operator overloading. *Shows:* dunder operators, `@` (`__matmul__`), `total_ordering`, `__iter__`. *vs:* operator overloads in C#.
- **023 · Inventory with Protocols**: storage backends swapped through structural typing. *Shows:* `typing.Protocol` vs `abc.ABC`, PEP 695 generics. *vs:* C# interfaces, TS structural types.
- **024 · Order Workflow State Machine**: valid transitions, history and a text diagram. *Shows:* `Enum`, `match`, transition tables, `assert_never`. *vs:* Stateless library, XState.
- **025 · Plugin Text Pipeline**: auto-registered text transforms that chain from the CLI. *Shows:* `__init_subclass__` registries, `importlib`, entry points. *vs:* assembly scanning / MEF.
- **026 · Typed Event Bus**: publish/subscribe with typed events and weak subscribers. *Shows:* generics, `Callable`, `ParamSpec`, `weakref`. *vs:* C# events/delegates, EventEmitter.
- **027 · Shape Calculator with Tagged Unions**: an exhaustive `match` over shape variants. *Shows:* dataclass unions, `match` class patterns, mypy strict exhaustiveness. *vs:* TS discriminated unions.
- **028 · Game of Life**: an animated terminal simulation on an infinite board. *Shows:* `frozenset` of coordinates, set algebra, generators, terminal control codes. *vs:* 2D arrays.
- **029 · Money & Currency Library**: currency-safe arithmetic with custom formatting. *Shows:* `Decimal` contexts, `__format__` specs, `__hash__`/`__eq__`. *vs:* NodaMoney, dinero.js.
- **030 · Undo/Redo Text Editor Core**: editor commands with an undo stack and transactions. *Shows:* the command pattern with closures, `deque`, `contextmanager`. *vs:* ICommand.

## Phase 4: Command line, automation and TUIs (days 31–40)

- **031 · Polished CLI with Typer + Rich**: a task CLI with tables, colours and progress bars. *Shows:* Typer (type hints → CLI), Rich rendering. *vs:* Spectre.Console, commander + chalk.
- **032 · Git Repository Insights**: commit stats, top authors and churn hotspots. *Shows:* `subprocess.run`, parsing `git log`, Rich charts. *vs:* `Process.Start`, `child_process`.
- **033 · Bulk File Renamer**: regex renames with a coloured preview diff and undo log. *Shows:* `re.sub` with functions, dry runs, JSON undo journal. *vs:* PowerShell `Rename-Item`.
- **034 · Downloads Auto-Organizer**: watches a folder and files things by rules. *Shows:* `watchdog`, `logging` configuration, rule matching. *vs:* `FileSystemWatcher`, chokidar.
- **035 · Backup Tool with Retention**: zips folders on a schedule and prunes old archives. *Shows:* `shutil.make_archive`, `zipfile`, retention maths with `datetime`. *vs:* hosted services / cron.
- **036 · Web Scraper**: scrapes books.toscrape.com into CSV, politely. *Shows:* `httpx` + `selectolax`, pagination generators, rate limiting. *vs:* AngleSharp, cheerio.
- **037 · Textual Todo App**: a full-screen terminal UI with keyboard bindings and tests. *Shows:* Textual widgets, CSS, Pilot tests. *vs:* Terminal.Gui, Ink.
- **038 · Pomodoro Timer TUI**: a timer with reactive state, notifications and stats. *Shows:* Textual reactive attributes and timers. *vs:* `INotifyPropertyChanged`, React state.
- **039 · Dotfiles Manager**: symlinks configs from a repo, idempotently, with a dry run. *Shows:* `pathlib` symlinks, TOML config, idempotent design. *vs:* PowerShell DSC.
- **040 · System Monitor Dashboard**: live CPU, memory, disk and process view. *Shows:* `psutil`, Rich `Live` layouts. *vs:* PerformanceCounter, `os` module.

## Phase 5: Web and APIs (days 41–50)

- **041 · Notes API with FastAPI**: CRUD with automatic OpenAPI docs. *Shows:* FastAPI routes, Pydantic models, dependency injection. *vs:* ASP.NET minimal APIs, Express + zod.
- **042 · URL Shortener**: short links, redirects and click stats on SQLite. *Shows:* SQLModel, validation, `RedirectResponse`. *vs:* EF Core + minimal API.
- **043 · Validation Service with Pydantic**: validates complex payloads and emits JSON Schema. *Shows:* validators, discriminated unions, `model_json_schema`. *vs:* FluentValidation, zod.
- **044 · Authenticated API**: password login, JWT access tokens and protected routes. *Shows:* OAuth2 password flow, `pyjwt`, argon2 hashing, `Depends`. *vs:* ASP.NET Identity, Passport.
- **045 · Guestbook with Jinja2 + HTMX**: server-rendered pages with partial updates. *Shows:* Jinja2 templates, HTMX endpoints. *vs:* Razor Pages, Next.js server components.
- **046 · Micro-blog in Flask**: the same idea in Flask, to compare frameworks. *Shows:* Flask blueprints, app factory, sessions. *vs:* Express.
- **047 · Recipe Box in Django**: models, admin site and migrations in one day. *Shows:* Django ORM, admin, `manage.py`. *vs:* ASP.NET MVC + EF scaffolding.
- **048 · GraphQL API**: books and authors with Strawberry. *Shows:* type-hint-driven schemas, resolvers, dataloaders. *vs:* Hot Chocolate, Apollo Server.
- **049 · Webhook Receiver**: verifies HMAC signatures and processes events in the background. *Shows:* `hmac.compare_digest`, background tasks, idempotency keys. *vs:* Stripe webhooks in ASP.NET.
- **050 · Typed API Client SDK**: a typed client with retries, pagination and mocks. *Shows:* `httpx`, `tenacity`, generator pagination, `respx` tests. *vs:* Refit + Polly, ky.

## Phase 6: Async and concurrency (days 51–60)

- **051 · Async Uptime Checker**: checks hundreds of URLs concurrently with limits. *Shows:* `asyncio.gather`, `Semaphore`, `httpx.AsyncClient`. *vs:* `Task.WhenAll`, `Promise.allSettled`.
- **052 · Concurrent Web Crawler**: a bounded-depth crawler with a work queue. *Shows:* `TaskGroup`, `asyncio.Queue`, structured cancellation. *vs:* `Channel<T>`, p-queue.
- **053 · WebSocket Chat**: a multi-room chat server with a browser client. *Shows:* FastAPI WebSockets, broadcast fan-out. *vs:* SignalR, socket.io.
- **054 · Rate Limiter Library**: token bucket and sliding window, sync and async. *Shows:* decorators for both function kinds, fake clocks in tests. *vs:* `System.Threading.RateLimiting`.
- **055 · Streaming ETL Pipeline**: producer → transform → sink with backpressure and graceful shutdown. *Shows:* bounded queues, signal handling, `asyncio.timeout`. *vs:* TPL Dataflow, Node streams.
- **056 · Parallel Image Processing Benchmark**: threads vs processes vs (free-threaded) threads. *Shows:* the GIL in practice, `ProcessPoolExecutor`, `InterpreterPoolExecutor`. *vs:* `Parallel.ForEach`, worker_threads.
- **057 · Persistent Job Queue**: SQLite-backed jobs with workers, retries and backoff. *Shows:* `aiosqlite`, retry policies, `asyncio.to_thread`. *vs:* Hangfire, BullMQ.
- **058 · Live Ticker with Server-Sent Events**: a simulated price stream pushed to a browser chart. *Shows:* async generators, SSE responses. *vs:* `IAsyncEnumerable` streaming.
- **059 · Sub-interpreter Worker Pool**: CPU work in isolated interpreters (3.14). *Shows:* `concurrent.interpreters`, channels, isolation trade-offs. *vs:* AppDomains, isolates.
- **060 · Mini Redis**: an async TCP key-value server with its own protocol and client. *Shows:* `asyncio` streams, protocol parsing, TTL expiry. *vs:* `TcpListener`, `net.createServer`.

## Phase 7: Data, science and ML (days 61–70)

- **061 · Mandelbrot Renderer**: a NumPy-vectorised fractal saved as PNG, with timings. *Shows:* NumPy broadcasting vs Python loops. *vs:* `Vector<T>` / SIMD.
- **062 · Sales Analysis with pandas**: a bundled dataset: cleaning, groupby, pivots. *Shows:* DataFrames, method chaining. *vs:* LINQ over lists, lodash.
- **063 · Same Analysis with Polars**: the lazy query engine compared with pandas. *Shows:* Polars expressions, lazy plans, speed. *vs:* `IQueryable` expression trees.
- **064 · Charts Report**: a static HTML report with Plotly and Matplotlib charts. *Shows:* plotting APIs, templated HTML output. *vs:* Chart.js, ScottPlot.
- **065 · Reactive Notebook with marimo**: an interactive data notebook stored as a .py file. *Shows:* marimo reactivity, notebooks vs scripts. *vs:* Polyglot Notebooks.
- **066 · Data Explorer in Streamlit**: upload a CSV, filter it, chart it, from a ~100-line script. *Shows:* the Streamlit execution model. *vs:* Blazor Server.
- **067 · Monte Carlo Simulator**: estimates project delivery dates from task estimates. *Shows:* `random`, `statistics`, NumPy, percentiles. *vs:* Math.NET.
- **068 · Text Classifier**: spam vs ham with TF-IDF and logistic regression. *Shows:* a scikit-learn pipeline, train/test split, metrics. *vs:* ML.NET.
- **069 · Model Serving**: the day-068 model persisted and served behind a FastAPI endpoint. *Shows:* `joblib`, input validation, model versioning. *vs:* ML.NET PredictionEngine.
- **070 · Interactive Map**: geocoded places from a CSV rendered to an HTML map. *Shows:* `folium`, GeoJSON. *vs:* Leaflet directly.

## Phase 8: Quality, testing and shipping (days 71–80)

- **071 · Property-based Testing**: Hypothesis finds edge-case bugs in a date-range parser. *Shows:* `hypothesis` strategies, shrinking. *vs:* FsCheck, fast-check.
- **072 · Testing a FastAPI App**: fixtures, factories, TestClient and coverage. *Shows:* pytest fixture scopes, dependency overrides. *vs:* WebApplicationFactory, supertest.
- **073 · Time & Snapshot Testing**: freezing time and golden-file tests. *Shows:* `time-machine`, `syrupy` snapshots. *vs:* `TimeProvider`, Jest snapshots.
- **074 · Publishable Library**: a src-layout package with versioning and a changelog, built with `uv build`. *Shows:* packaging metadata, wheels vs sdists, TestPyPI steps. *vs:* `dotnet pack`, `npm publish`.
- **075 · Installable CLI Tool**: `uv tool install .` with shell completion. *Shows:* entry points, `importlib.metadata`. *vs:* dotnet global tools, npm bin.
- **076 · Profiling & Optimization**: a slow program made 20× faster, step by step. *Shows:* `cProfile`, `pstats`, `functools.cache`, algorithmic fixes. *vs:* dotTrace, Chrome profiler.
- **077 · Structured Logging & Tracing**: JSON logs and OpenTelemetry spans to the console. *Shows:* `structlog`, OpenTelemetry SDK. *vs:* Serilog, pino.
- **078 · CI Quality Gate**: pre-commit hooks plus a GitHub Actions workflow (generated, not pushed). *Shows:* ruff, mypy strict, pytest in CI with uv caching. *vs:* Azure Pipelines, Husky.
- **079 · Dockerized API**: a multi-stage Dockerfile using uv, a health check and a slim image. *Shows:* Python container best practices. *vs:* .NET chiseled images.
- **080 · Documentation Site**: MkDocs Material with API docs generated from docstrings. *Shows:* `mkdocstrings`, docstring conventions. *vs:* DocFX, TypeDoc.

## Phase 9: Advanced Python (days 81–90)

- **081 · Tiny ORM**: models with descriptors mapping to SQLite tables. *Shows:* descriptors, `__set_name__`, `__init_subclass__`. *vs:* EF Core conventions.
- **082 · Dependency Injection Container**: resolves constructors from type hints. *Shows:* `inspect.signature`, `typing.get_type_hints`, scopes. *vs:* `Microsoft.Extensions.DependencyInjection`.
- **083 · Template Engine**: compiles `{{ }}` templates into Python functions. *Shows:* tokenising, code generation, `compile`/`exec` with care. *vs:* Razor compilation.
- **084 · Expression Language**: lexer, Pratt parser and evaluator for a small calculator language. *Shows:* dataclass ASTs, `match`, recursion. *vs:* Roslyn syntax trees.
- **085 · Mini Test Runner**: discovers tests and rewrites asserts with `ast`. *Shows:* the `ast` module, import hooks, introspection. *vs:* xUnit discovery.
- **086 · Decorator Toolkit**: retry, timeout, TTL memoize and validation, all fully typed. *Shows:* `ParamSpec`, `Concatenate`, `functools.wraps`. *vs:* Polly, aspect-oriented programming.
- **087 · Calling C**: a C function compiled at runtime and called through `ctypes`, with benchmarks. *Shows:* `ctypes`, the FFI boundary cost. *vs:* P/Invoke, N-API.
- **088 · Free-threaded Python**: the same CPU-bound threads on 3.14 and 3.14t. *Shows:* the GIL removal in practice, thread safety. *vs:* .NET threads.
- **089 · Build an Event Loop**: a toy asyncio built from generators. *Shows:* `yield`, `send`, a scheduler and a selector. *vs:* how `async`/`await` compiles in C#.
- **090 · Import Hooks**: `import settings` loads `settings.toml` as a module. *Shows:* `importlib` finders and loaders, `sys.meta_path`. *vs:* source generators.

## Phase 10: Capstone apps (days 91–100)

- **091 · Snake in the Terminal**: a curses game with speed levels and high scores. *Shows:* `curses`, game loops, `collections.deque`. *vs:* Console games in C#.
- **092 · Breakout with pygame**: sprites, collisions and sound. *Shows:* `pygame-ce`, fixed-timestep loops. *vs:* MonoGame, Phaser.
- **093 · Desktop App with tkinter**: an expense tracker GUI using only the standard library. *Shows:* tkinter/ttk, MVC separation. *vs:* WinForms/WPF, Electron.
- **094 · Claude Chat CLI**: streaming chat with tool calls through the Anthropic SDK, plus an offline mock mode. *Shows:* the `anthropic` SDK, streaming, tool use. *vs:* Semantic Kernel.
- **095 · Search Your Notes**: BM25 search over the lessons and days, with an optional Claude answer. *Shows:* tokenising, ranking, `rank-bm25`. *vs:* Lucene.NET.
- **096 · Static Site Generator**: Markdown → HTML with templates, a watch mode and live reload. *Shows:* `markdown-it-py`, Jinja2, file watching. *vs:* Statiq, Eleventy.
- **097 · Personal Finance Dashboard**: imports bank CSVs, auto-categorises and charts spending. *Shows:* pandas, rules engine, Streamlit. *vs:* Power BI.
- **098 · Kanban Board**: FastAPI + SQLModel + HTMX drag-and-drop board. *Shows:* full-stack Python without a JS build step. *vs:* ASP.NET + React.
- **099 · Multiplayer Tic-Tac-Toe**: WebSocket game server with lobbies and a browser client. *Shows:* async state, broadcast, reconnects. *vs:* SignalR games.
- **100 · 100 Days Retrospective**: analyses this repo itself (lines of code, libraries, features used) and renders a report site. *Shows:* `ast` analysis, everything combined. *vs:* Roslyn analyzers.
