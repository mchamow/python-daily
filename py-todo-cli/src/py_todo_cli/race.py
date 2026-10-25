"""Race demo: many writers add a task each, with and without the lock and atomic write.

    uv run python -m py_todo_cli.race

Threads stand in for separate processes here. flock() locks belong to an *open file*, not to
a process, so two threads that each open the lock file contend exactly like two terminals would.
"""

import sys
import tempfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from .storage import StorageError, editing, load


def race(path: Path, *, safe: bool, writers: int = 64) -> tuple[int | None, Counter[str], str]:
    """Returns (tasks kept or None if unreadable, crashes by error type, final file state)."""

    def add_one(i: int) -> str | None:
        try:
            with editing(path, safe=safe) as todo:
                todo.add(f"task {i}", now=datetime.now(UTC))
        except Exception as error:  # a demo wants to count failures, not stop at the first
            return type(error.__cause__ or error).__name__  # the root cause, e.g. a JSON error
        return None

    with ThreadPoolExecutor(max_workers=16) as pool:
        crashes = Counter(error for error in pool.map(add_one, range(writers)) if error)
    try:
        kept: int | None = len(load(path).tasks)
        state = "valid JSON"
    except StorageError as error:
        kept, state = None, f"CORRUPT ({error.__cause__})"
    return kept, crashes, state


def main(writers: int = 64) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        for safe, label in ((False, "plain write_text, no lock"), (True, "lock + atomic replace")):
            kept, crashes, state = race(Path(tmp) / f"{safe}.json", safe=safe, writers=writers)
            crashed = ", ".join(f"{n} {name}" for name, n in crashes.items()) or "none"
            print(f"{label}:")
            shown = "unknown, the file can't be read" if kept is None else f"{kept} of {writers}"
            print(f"  tasks kept    {shown}")
            print(f"  writers died  {crashed}")
            print(f"  final file    {state}")


if __name__ == "__main__":  # true only when run as a script or with python -m
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 64)
