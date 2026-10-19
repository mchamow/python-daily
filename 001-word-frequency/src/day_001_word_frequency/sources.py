"""Where text comes from: files, directories (searched recursively) or stdin."""

import sys
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO


@dataclass(frozen=True, slots=True)
class Source:
    name: str
    text: str


class SourceError(Exception):
    """An input that can't be read; the message is ready to show to the user."""


def iter_sources(
    specs: Iterable[str], *, pattern: str = "*.txt", stdin: TextIO | None = None
) -> Iterator[Source]:
    """Expand each command-line argument into one or more Sources.

    "-" reads stdin, a directory is searched recursively for `pattern`, anything else
    must be a file. Files inside a directory are yielded in sorted order, so output
    is the same on every OS.
    """
    for spec in specs:
        if spec == "-":
            yield Source("<stdin>", (stdin or sys.stdin).read())
            continue
        path = Path(spec)
        if path.is_dir():
            files = sorted(p for p in path.rglob(pattern) if p.is_file())
            if not files:
                raise SourceError(f"{path}: no files matching {pattern!r}")
            yield from (_read(f) for f in files)
        elif path.is_file():
            yield _read(path)
        else:
            raise SourceError(f"{spec}: no such file or directory")


def _read(path: Path) -> Source:
    try:
        # errors="replace": one bad byte in a big log shouldn't abort the whole run.
        return Source(str(path), path.read_text(encoding="utf-8", errors="replace"))
    except OSError as e:
        raise SourceError(f"{path}: {e.strerror}") from e
