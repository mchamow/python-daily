"""Stream every file with ``os.walk``: the flat, lazy alternative to building a tree.

When you don't need per-directory totals, a tree is wasted memory. ``iter_files`` is a
generator, so ``heapq.nlargest(10, iter_files(...))`` scans a million files while holding ten.
"""

import heapq
import os
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from operator import attrgetter
from pathlib import Path

from .scan import Options, Problem, excluded, first_sighting, usage
from .size import Size


@dataclass(frozen=True, slots=True)
class File:
    path: str
    size: Size


def iter_files(
    root: Path, options: Options, on_error: Callable[[Problem], object]
) -> Iterator[File]:
    """Yield every file and symlink under ``root``, lazily, top-down.

    Unreadable entries go to ``on_error`` (e.g. ``problems.append``) and the walk carries on.
    """
    seen: set[tuple[int, int]] = set()
    top_dev = root.lstat().st_dev

    def report(error: OSError) -> None:
        on_error(Problem.of(error))

    for dirpath, dirnames, filenames in os.walk(root, onerror=report):
        # Prune *in place*: os.walk recurses into whatever this same list holds after the yield.
        # `dirnames = [...]` would rebind a local name and prune nothing.
        dirnames[:] = [
            d
            for d in dirnames
            if not excluded(d, options.exclude)
            and not (options.one_file_system and other_device(dirpath, d, top_dev))
        ]
        for name in filenames:
            if excluded(name, options.exclude):
                continue
            path = os.path.join(dirpath, name)
            try:
                st = os.lstat(path)  # os.walk only hands us names; sizes cost a stat each
            except OSError as e:
                report(e)
                continue
            if first_sighting(st, seen):
                yield File(path, Size(usage(st, apparent=options.apparent)))


def other_device(dirpath: str, name: str, dev: int) -> bool:
    try:
        return os.lstat(os.path.join(dirpath, name)).st_dev != dev
    except OSError:
        return True  # can't stat it, so don't walk into it either


def largest(
    root: Path, n: int, options: Options, on_error: Callable[[Problem], object]
) -> list[File]:
    """The ``n`` biggest files, biggest first, in O(n) memory however many files there are."""
    return heapq.nlargest(n, iter_files(root, options, on_error), key=attrgetter("size"))
