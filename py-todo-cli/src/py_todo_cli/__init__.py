"""todo: a small todo list in a JSON file (add, list, done, rm, clear)."""

import argparse
import os
import sys
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path

from .codec import dumps
from .dates import describe_due, parse_due
from .model import Priority, Task, sort_key
from .storage import StorageError, editing, load

type Handler = Callable[[argparse.Namespace, Path, datetime], str]


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    # --file is SUPPRESSed by default (see _parser), so the attribute may be absent entirely.
    path: Path = getattr(args, "file", None) or default_path()
    handler: Handler = args.handler  # Namespace attributes are Any: pin the type at the edge
    now = datetime.now().astimezone().replace(microsecond=0)  # aware, in the local timezone
    try:
        print(handler(args, path, now))
    except (StorageError, LookupError, ValueError) as error:
        print(f"todo: {error}", file=sys.stderr)
        return 1
    return 0


def default_path() -> Path:
    return Path(os.environ.get("TODO_FILE", Path.home() / ".todo.json"))


def _parser() -> argparse.ArgumentParser:
    # Options shared by every command. Added to the main parser *and* each subparser, so
    # 'todo -f x.json list' and 'todo list -f x.json' both work. default=SUPPRESS stops a
    # subparser's default from overwriting a value the main parser already parsed.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "-f",
        "--file",
        type=Path,
        default=argparse.SUPPRESS,
        help="todo file (default: $TODO_FILE or ~/.todo.json)",
    )

    parser = argparse.ArgumentParser(
        prog="todo", description=__doc__, parents=[common], suggest_on_error=True
    )
    commands = parser.add_subparsers(title="commands", required=True)

    add = commands.add_parser("add", parents=[common], help="add a task")
    add.add_argument("title", nargs="+", help="words of the title (quotes optional)")
    add.add_argument(
        "-p", "--priority", type=Priority, choices=list(Priority), default=Priority.NORMAL
    )
    add.add_argument("-t", "--tag", action="append", default=[], help="repeatable")
    add.add_argument("--due", help="YYYY-MM-DD, today, tomorrow, fri, +3d, +2w")
    add.set_defaults(handler=_add)

    ls = commands.add_parser("list", aliases=["ls"], parents=[common], help="show tasks")
    ls.add_argument("-a", "--all", action="store_true", help="include done tasks")
    ls.add_argument("-t", "--tag", help="only tasks with this tag")
    ls.add_argument("--json", action="store_true", help="machine-readable output")
    ls.set_defaults(handler=_list)

    for name, handler, text in (("done", _done, "mark tasks done"), ("rm", _rm, "delete tasks")):
        sub = commands.add_parser(name, parents=[common], help=text)
        sub.add_argument("ids", type=int, nargs="+", metavar="ID")
        sub.set_defaults(handler=handler)

    clear = commands.add_parser("clear", parents=[common], help="delete all done tasks")
    clear.set_defaults(handler=_clear)
    return parser


# --- command handlers: (args, path, now) -> text to print ------------------------------------


def _add(args: argparse.Namespace, path: Path, now: datetime) -> str:
    due = parse_due(args.due, now.date()) if args.due else None
    with editing(path) as todo:
        task = todo.add(
            " ".join(args.title), now=now, priority=args.priority, tags=args.tag, due=due
        )
    return f"added #{task.id}: {task.title}"


def _list(args: argparse.Namespace, path: Path, now: datetime) -> str:
    todo = load(path)  # read-only: no lock needed, because saves are atomic
    tasks = sorted(
        (
            t
            for t in todo.tasks
            if (args.all or not t.done) and (not args.tag or args.tag in t.tags)
        ),
        key=sort_key,
    )
    if args.json:
        return dumps(tasks).rstrip()
    hidden = sum(1 for t in todo.tasks if t.done) if not args.all else 0
    return render(tasks, now, hidden_done=hidden)


def _done(args: argparse.Namespace, path: Path, now: datetime) -> str:
    with editing(path) as todo:
        # If a later id doesn't exist, find() raises, editing() never saves, and the tasks
        # already marked here are thrown away with the in-memory copy: all or nothing.
        marked: list[Task] = []
        for task_id in args.ids:
            task = todo.find(task_id)
            task.done = task.done or now
            marked.append(task)
    return "\n".join(f"done #{t.id}: {t.title}" for t in marked)


def _rm(args: argparse.Namespace, path: Path, now: datetime) -> str:
    with editing(path) as todo:
        removed = todo.remove(args.ids)
    return "\n".join(f"removed #{t.id}: {t.title}" for t in removed)


def _clear(args: argparse.Namespace, path: Path, now: datetime) -> str:
    with editing(path) as todo:
        cleared = todo.clear_done()
    return f"cleared {len(cleared)} done task(s)"


def render(tasks: list[Task], now: datetime, *, hidden_done: int = 0) -> str:
    if not tasks:
        return "nothing to do" + (
            f" ({hidden_done} done, 'todo list --all' shows them)" if hidden_done else ""
        )
    rows = [
        (
            "[x]" if t.done else "[ ]",
            f"#{t.id}",
            "" if t.priority is Priority.NORMAL else t.priority,
            describe_due(t.due, now.date()) if t.due and not t.done else "",
            " ".join([t.title, *(f"#{tag}" for tag in t.tags)]),
        )
        for t in tasks
    ]
    # zip(*rows) transposes rows into columns, so each width is one max() per column.
    widths = [max(map(len, column)) for column in zip(*rows, strict=True)]
    lines = [
        "  ".join(cell.ljust(w) for cell, w in zip(row, widths, strict=True)).rstrip()
        for row in rows
    ]
    if hidden_done:
        lines.append(f"(+{hidden_done} done, 'todo list --all' shows them)")
    return "\n".join(lines)
