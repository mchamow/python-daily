"""Load and save the todo file without ever leaving it half-written.

Two separate problems, two separate fixes:

- **Crashes.** ``write_text`` truncates the file and then writes it. Die in between and the file
  is empty or cut short. So we write a temp file next to it and ``os.replace`` it into place,
  which is atomic: readers see the old file or the new one, never a mix.
- **Concurrent writers.** Two processes that both load, change and save will lose one change
  (last writer wins), atomic or not. So editing holds an exclusive lock for the whole
  load-change-save cycle.
"""

import json
import os
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import IO

from .codec import DecodeError, dumps, loads
from .model import SCHEMA_VERSION, TodoFile

if sys.platform == "win32":  # mypy understands this check and only type-checks one branch
    import msvcrt

    def _lock(file: IO[bytes]) -> None:
        msvcrt.locking(file.fileno(), msvcrt.LK_LOCK, 1)

else:
    import fcntl

    def _lock(file: IO[bytes]) -> None:
        fcntl.flock(file.fileno(), fcntl.LOCK_EX)  # blocks until the other process is done


class StorageError(Exception):
    pass


def load(path: Path) -> TodoFile:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return TodoFile()  # first run: nothing saved yet
    try:
        todo = loads(TodoFile, text)
    except json.JSONDecodeError as error:
        raise StorageError(f"{path} is not valid JSON ({error})") from error
    except DecodeError as error:
        raise StorageError(f"{path} doesn't look like a todo file: {error}") from error
    if todo.version != SCHEMA_VERSION:
        raise StorageError(f"{path} is version {todo.version}; this todo reads {SCHEMA_VERSION}")
    return todo


def save(path: Path, todo: TodoFile) -> None:
    """Write to a temp file in the same directory, flush it to disk, then swap it in."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # Same directory matters: a rename is only atomic within one filesystem.
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as tmp:
        tmp.write(dumps(todo))
        tmp.flush()
        os.fsync(tmp.fileno())  # otherwise the rename can hit the disk before the data does
    try:
        os.replace(tmp.name, path)  # atomic, and overwrites on Windows too (os.rename doesn't)
    except BaseException:
        os.unlink(tmp.name)
        raise


@contextmanager
def locked(path: Path) -> Iterator[None]:
    """Hold an exclusive lock on ``<path>.lock`` while the with-block runs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # Lock a sidecar file, not the data file: os.replace swaps the data file's inode, so a lock
    # on it would protect a file nobody reads any more.
    with path.with_name(path.name + ".lock").open("ab") as lock_file:
        _lock(lock_file)
        yield  # the lock is released when the file is closed, even if the block raised


@contextmanager
def editing(path: Path, *, safe: bool = True) -> Iterator[TodoFile]:
    """Load, let the with-block change it, save. If the block raises, nothing is saved.

    ``safe=False`` skips the lock and the atomic write. It exists only for the race demo.
    """
    if not safe:
        todo = load(path)
        yield todo
        path.write_text(dumps(todo), encoding="utf-8")
        return
    with locked(path):
        todo = load(path)
        yield todo
        save(path, todo)
