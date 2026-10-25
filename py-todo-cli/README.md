# Day 004 · Todo CLI with JSON Storage

`todo` keeps a todo list in a JSON file. It decodes the file back into typed dataclasses, makes
every change all-or-nothing, and survives dozens of simultaneous writers without losing a task.

## Run it

```bash
cd py-todo-cli
export TODO_FILE=demo.json             # otherwise it uses ~/.todo.json (demo.json is gitignored)
uv run todo add Renew passport -p high -t admin --due 2026-10-20
uv run todo add Buy oat milk -t home --due tomorrow
uv run todo list                       # or: ls, ls --all, ls -t home, ls --json
uv run todo done 2
uv run todo rm 1
uv run todo clear                      # delete everything that's done
uv run todo -f data/todo.json ls --all # the bundled sample file
uv run python -m py_todo_cli.race      # 64 concurrent writers, without and with the lock
uv run pytest
```

Due dates accept `2026-12-24`, `today`, `tomorrow`, a weekday (`fri`, `friday`), `+3d` or `+2w`.

## What it looks like

```text
$ uv run todo add Renew passport -p high -t admin --due 2026-10-20
added #1: Renew passport
$ uv run todo add Buy oat milk -t home --due tomorrow
added #2: Buy oat milk
$ uv run todo add Write the day 4 README -t python --due fri
added #3: Write the day 4 README
$ uv run todo add Read PEP 695 -p low -t python
added #4: Read PEP 695
$ uv run todo list
[ ]  #1  high  overdue 5d  Renew passport #admin
[ ]  #2        tomorrow    Buy oat milk #home
[ ]  #3        fri         Write the day 4 README #python
[ ]  #4  low               Read PEP 695 #python
$ uv run todo done 2 99
todo: no task #99
$ uv run todo done 2
done #2: Buy oat milk
$ uv run todo ls
[ ]  #1  high  overdue 5d  Renew passport #admin
[ ]  #3        fri         Write the day 4 README #python
[ ]  #4  low               Read PEP 695 #python
(+1 done, 'todo list --all' shows them)
$ uv run todo lst
usage: todo [-h] [-f FILE] {add,list,ls,done,rm,clear} ...
todo: error: argument {add,list,ls,done,rm,clear}: invalid choice: 'lst', maybe you meant 'list'? (choose from 'add', 'list', 'ls', 'done', 'rm', 'clear')
$ uv run todo add Call mum --due someday
todo: can't read due date 'someday': use YYYY-MM-DD, today, tomorrow, a weekday or +3d
```

Note `done 2 99`: task #2 exists and #99 doesn't, so the command fails and **#2 is not marked
either**. Every change runs inside one load-change-save transaction, and a failure anywhere
inside it discards the whole thing.

The file is plain, diffable JSON, and the list can be exported the same way:

```text
$ cat demo.json
{
  "version": 1,
  "next_id": 5,
  "tasks": [
    {
      "id": 1,
      "title": "Renew passport",
      "created": "2026-10-25T08:46:44+01:00",
      "priority": "high",
      "tags": [
        "admin"
      ],
      "due": "2026-10-20",
      "done": null
    },
    ...
$ uv run todo ls --json -t python
[
  {
    "id": 3,
    "title": "Write the day 4 README",
    "created": "2026-10-25T08:46:44+01:00",
    "priority": "normal",
    ...
```

And here's the standout. The race demo runs 64 writers at once, each adding one task. First
they do the obvious thing (`load`, change, `path.write_text`), then they go through `editing()`,
which takes a lock and writes atomically:

```text
$ uv run python -m py_todo_cli.race
plain write_text, no lock:
  tasks kept    unknown, the file can't be read
  writers died  49 JSONDecodeError
  final file    CORRUPT (Extra data: line 62 column 7 (char 1202))
lock + atomic replace:
  tasks kept    64 of 64
  writers died  none
  final file    valid JSON
```

The naive version's numbers change from run to run. Over three runs it kept 9 tasks, then 8, and
once none at all, because the file ended up as two JSON documents glued together. The safe version keeps
64 of 64 every time. The naive pattern is what most quick scripts do, and it fails in two
different ways, which the code tour takes apart.

## What you'll learn

- **Dataclasses as the model**: `slots=True`, `field(default_factory=list)` and a `StrEnum`
  that serialises as a plain string ([model.py#L23](src/py_todo_cli/model.py#L23)).
- **Dataclasses ↔ JSON with only the stdlib**: a `default=` hook to encode, and a strict
  decoder driven by `get_type_hints` that reports errors as paths like `$.tasks[3].due`
  ([codec.py#L28](src/py_todo_cli/codec.py#L28), [codec.py#L43](src/py_todo_cli/codec.py#L43)).
- **Atomic writes**: `NamedTemporaryFile` in the same directory, `fsync`, then `os.replace`
  ([storage.py#L58](src/py_todo_cli/storage.py#L58)).
- **Transactions with `@contextmanager`**: lock, load, `yield`, save; an exception skips the save
  ([storage.py#L87](src/py_todo_cli/storage.py#L87)).
- **`argparse` subparsers**: `set_defaults(handler=...)` dispatch, shared options through
  `parents=`, and 3.14's `suggest_on_error` ([\_\_init\_\_.py#L36](src/py_todo_cli/__init__.py#L36)).
- **`match` with guards and the walrus**: due-date parsing in one statement
  ([dates.py#L13](src/py_todo_cli/dates.py#L13)).

## Code tour

### 1. The model: dataclasses and a `StrEnum`

```python
class Priority(StrEnum):
    LOW = auto()  # auto() on a StrEnum gives the lowercased name: "low"
    NORMAL = auto()
    HIGH = auto()


@dataclass(slots=True)
class Task:
    id: int
    title: str
    created: datetime
    priority: Priority = Priority.NORMAL
    tags: list[str] = field(default_factory=list)  # never `= []`
    due: date | None = None
    done: datetime | None = None
```

`@dataclass` writes `__init__`, `__repr__` and `__eq__` from the annotations, much like a C#
`record class`. Unlike a record it stays mutable, which suits `task.done = now`.

`slots=True` drops the per-instance `__dict__`. Objects get smaller, and a typo like
`task.dne = now` raises `AttributeError` instead of silently creating a new attribute.

`Priority` is a `StrEnum`, so its members *are* strings: `Priority.HIGH == "high"`, and
`json.dumps` writes them without any help. A C# enum serialises as an int unless you add
`JsonStringEnumConverter`.

`field(default_factory=list)` is the fix for Python's best-known trap; see Gotchas.

### 2. Encoding is a hook, decoding is a walk over the type hints

```python
def _encode(value: object) -> object:
    match value:
        case date():  # datetime is a subclass of date, so this covers both
            return value.isoformat()
        case _ if is_dataclass(value) and not isinstance(value, type):
            return asdict(value)
    raise TypeError(f"can't encode {type(value).__name__} as JSON")
```

`json.dumps(obj, default=_encode)` calls the hook only for values it can't serialise, then
serialises whatever the hook returns. That covers a whole `TodoFile`, a bare `list[Task]` for
`ls --json`, and the dates inside both.

Decoding is the half that Python's stdlib leaves to you. `json.loads` returns dicts and strings.
It knows nothing about `Task` or `date`, and System.Text.Json's `Deserialize<T>` has no
built-in equivalent. So `decode` reads the class's own annotations:

```python
hints = get_type_hints(cls)  # {'id': int, 'due': date | None, 'tags': list[str], ...}
for f in fields(cls):
    if f.name in data:
        values[f.name] = _convert(hints[f.name], data[f.name], f"{path}.{f.name}")
    elif f.default is MISSING and f.default_factory is MISSING:
        raise DecodeError(f"{path}.{f.name}: missing")
return cls(**values)
```

`_convert` takes the type apart with `get_origin` and `get_args`. `date | None` has origin
`UnionType` and args `(date, NoneType)`, and `list[str]` has origin `list`. It recurses into
lists and nested dataclasses, so errors read like `$.tasks[0].priority: expected one of low,
normal, high, got 'urgent'`. The whole module is under 100 lines. In a real project you'd use `pydantic` or
`msgspec`, which do this (and much more) from the same annotations. Writing it once shows you
that type hints are ordinary runtime data.

`decode[T: DataclassInstance]` is 3.12+ generic syntax, and `DataclassInstance` is imported only
under `TYPE_CHECKING`. That works because 3.14 evaluates annotations and bounds lazily, so a
name that only exists for the type checker never has to exist at runtime.

### 3. Atomic writes: temp file, `fsync`, `os.replace`

```python
with tempfile.NamedTemporaryFile(
    "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
) as tmp:
    tmp.write(dumps(todo))
    tmp.flush()
    os.fsync(tmp.fileno())
try:
    os.replace(tmp.name, path)
except BaseException:
    os.unlink(tmp.name)
    raise
```

`path.write_text(...)` opens the file with `O_TRUNC`, which empties it first, and then writes
it. Anyone reading in between, or a crash in between, sees an empty or half-written file. That
gave the race demo its `JSONDecodeError`s.

The fix is the classic one. Write a temp file *in the same directory*, because a rename is only
atomic within one filesystem. Flush Python's buffer, `fsync` the OS buffer to disk, then
`os.replace`, a single rename. Every reader sees either the complete old file or the complete
new one. Use `os.replace` rather than `os.rename`: `replace` overwrites on every platform, and
`rename` fails on Windows if the target exists. `except BaseException` also cleans up on
Ctrl-C, which raises `KeyboardInterrupt` rather than an `Exception`.

### 4. A transaction in eight lines: `@contextmanager`

```python
@contextmanager
def editing(path: Path, *, safe: bool = True) -> Iterator[TodoFile]:
    ...
    with locked(path):
        todo = load(path)
        yield todo
        save(path, todo)
```

Atomic writes alone don't stop *lost updates*. When two processes both load, both add a task
and both save, the second save wins and one task vanishes. So `editing` holds an exclusive
`fcntl.flock` (`msvcrt.locking` on Windows) across the whole load-change-save cycle.

`@contextmanager` turns a generator into a `with`-able object. Code before `yield` is the
setup, the yielded value is what `as` binds, and code after `yield` runs when the block ends
normally. If the block raises, the exception surfaces *at the `yield`*, so `save` never runs
and the lock still unwinds. That's why `todo done 2 99` changes nothing:

```python
with editing(path) as todo:
    for task_id in args.ids:
        task = todo.find(task_id)  # raises TaskNotFound for 99...
        task.done = task.done or now  # ...after #2 was marked in memory, which is just dropped
```

In C# you'd write a class implementing `IDisposable`, with a flag recording whether to commit.
Here a generator function is the whole thing.

The lock is on a sidecar `todo.json.lock`, not on `todo.json` itself, because `os.replace` swaps
in a new file. A lock on the old one would protect a file nobody reads any more.

### 5. `argparse`: subcommands, shared options, dispatch

```python
common = argparse.ArgumentParser(add_help=False)
common.add_argument("-f", "--file", type=Path, default=argparse.SUPPRESS, help=...)

parser = argparse.ArgumentParser(prog="todo", parents=[common], suggest_on_error=True)
commands = parser.add_subparsers(title="commands", required=True)
add = commands.add_parser("add", parents=[common], help="add a task")
add.add_argument("-p", "--priority", type=Priority, choices=list(Priority), default=Priority.NORMAL)
add.set_defaults(handler=_add)
...
handler: Handler = args.handler
```

Each subparser stores its handler function with `set_defaults`, so dispatch is `args.handler(...)`
with no `if`/`match` on the command name. `type=Priority` converts `"high"` to `Priority.HIGH`
during parsing. `suggest_on_error=True` (new in 3.14) gives the "maybe you meant 'list'?"
message.

`-f` is declared once in a `common` parent and attached to the main parser *and* every
subparser, so `todo -f x.json ls` and `todo ls -f x.json` both work. The `SUPPRESS` default
matters; see Gotchas.

`argparse.Namespace` is dynamically typed: every attribute is `Any`. The `handler: Handler`
annotation pins one type at the boundary, so mypy checks everything after it. With
System.CommandLine, values bind to typed parameters for you, and that's a real gap. Day-to-day
Python CLIs often use `typer` or `click` for exactly this reason.

## If you wrote this in C# / TypeScript

| Task | C# | TypeScript | Python |
| --- | --- | --- | --- |
| Data class | `record` / `class` with properties | `interface` + object literal | `@dataclass(slots=True)` |
| Enum as string in JSON | `JsonStringEnumConverter` | string-literal union | `StrEnum` (is a `str`) |
| Serialise | `JsonSerializer.Serialize(obj)` | `JSON.stringify(obj)` | `json.dumps(obj, default=hook)` |
| Typed deserialise | `JsonSerializer.Deserialize<T>()` | `JSON.parse` + cast (or zod) | none built in: hand-rolled, or pydantic / msgspec |
| Dates in JSON | ISO 8601 by default | strings; `new Date(s)` by hand | `isoformat()` / `fromisoformat()` by hand |
| Atomic replace | `File.Replace` / `File.Move(overwrite: true)` | `fs.rename` | `os.replace` |
| File lock | `FileShare.None` / `FileStream.Lock` | none built in (proper-lockfile) | `fcntl.flock` / `msvcrt.locking` |
| `using` scope with commit | `IDisposable` class | `try/finally` | `@contextmanager` generator |
| Subcommands | System.CommandLine `Command` + `SetHandler` | commander / yargs | `add_subparsers` + `set_defaults(handler=)` |

Loading the file, side by side:

```csharp
// C#: one call, typed, with converters configured once
var options = new JsonSerializerOptions { Converters = { new JsonStringEnumConverter() } };
var todo = JsonSerializer.Deserialize<TodoFile>(File.ReadAllText(path), options)
           ?? new TodoFile();
```

```typescript
// TypeScript: JSON.parse returns any; types are a promise, not a check
const todo = JSON.parse(await fs.readFile(path, "utf8")) as TodoFile; // due is still a string!
```

```python
todo = loads(TodoFile, path.read_text(encoding="utf-8"))  # our small decoder from codec.py
```

C# wins this one outright: typed deserialisation, ISO dates and string enums are a library
call. TypeScript and Python start in the same place, with `parse` returning untyped data. The
difference is that Python's annotations exist at runtime, so a decoder (yours, or pydantic's)
can read them and actually *check* the data, which a TS cast never does. On the storage side,
Python's `os.replace`, `tempfile` and `@contextmanager` make the safe version almost as short as
the unsafe one.

## Gotchas

- **Mutable defaults are shared.** In plain Python, `def add(tags=[])` evaluates `[]` once, when
  the function is defined, so every call shares the same list. `@dataclass` refuses
  `tags: list[str] = []` outright with a `ValueError`; that's why `field(default_factory=list)`
  exists. In a plain function, write `tags: list[str] | None = None`, as `TodoFile.add` does.
- **A subparser's default overwrites the parent's value.** If `-f` had `default=None` on both
  parsers, `todo -f x.json ls` would parse `x.json` and then let the `ls` subparser set `file`
  back to `None`. `default=argparse.SUPPRESS` means "don't set the attribute at all unless the
  flag is given". The price is that the attribute may be missing, hence
  `getattr(args, "file", None)`.
- **`bool` is an `int`.** `isinstance(True, int)` is `True`, so a check-based decoder would
  accept `"id": true` as task #1. The decoder compares `type(value) is int` instead. The same
  subclassing bites with dates: `isinstance(a_datetime, date)` is `True`, so test `datetime`
  before `date` whenever you branch on them.

## Your turn

1. **Easy:** add `todo undo ID...`, the opposite of `done`. Register it in the same loop as
   `done` and `rm`, set `task.done = None`, and extend `test_cli_flow` so that
   `done 1` → `undo 1` → `ls` shows #1 open again.
2. **Medium:** add `todo edit ID [--title …] [-p …] [--due …|--no-due] [-t …]`, and change
   only the fields that were given. Use `dataclasses.replace(task, **changes)`, building
   `changes` from the args that aren't `None`. Then make `--due` and `--no-due` mutually
   exclusive with `parser.add_mutually_exclusive_group()`.
3. **Stretch:** schema version 2: rename `done` to `completed_at` and add an optional `notes`
   field. Write `migrate(raw: dict) -> dict` that upgrades v1 data *before* `decode` sees it,
   call it in `load`, and save files back as v2. Test it with a v1 file in `tmp_path`, and
   check that a v3 file is still refused.

## Go deeper

- [`dataclasses`](https://docs.python.org/3/library/dataclasses.html) and
  [`enum.StrEnum`](https://docs.python.org/3/library/enum.html#enum.StrEnum)
- [`json`: the `default` hook](https://docs.python.org/3/library/json.html#json.dump) and
  [`typing.get_type_hints`](https://docs.python.org/3/library/typing.html#typing.get_type_hints)
- [`contextlib.contextmanager`](https://docs.python.org/3/library/contextlib.html#contextlib.contextmanager)
- [`os.replace`](https://docs.python.org/3/library/os.html#os.replace) and
  [`fcntl.flock`](https://docs.python.org/3/library/fcntl.html#fcntl.flock)
- [`argparse` sub-commands](https://docs.python.org/3/library/argparse.html#sub-commands)
- [msgspec](https://jcristharif.com/msgspec/) and [pydantic](https://docs.pydantic.dev/): what
  you'd use instead of `codec.py` in production
- Local lessons: lesson 07 (errors and context managers), lesson 04 (classes and OOP),
  lesson 05 (type hints).
