"""Build a size tree with recursive ``os.scandir``, counting bytes the way ``du`` does.

Recursion is the natural fit here: a directory's size is its own size plus what its children
return, so the totals fall out of the call stack. ``walk.py`` shows the flat ``os.walk`` way.
"""

import fnmatch
import os
import stat
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .size import Size


@dataclass(frozen=True, slots=True)
class Options:
    apparent: bool = False  # st_size (what `ls` says) instead of allocated blocks (what `du` says)
    one_file_system: bool = False  # like `du -x`: don't descend into other mounts
    exclude: tuple[str, ...] = ()  # glob patterns matched against names, e.g. ".git", "*.pyc"


DEFAULTS = Options()  # safe as a shared default only because it's frozen


@dataclass(slots=True)
class Node:
    name: str
    size: Size
    is_dir: bool = False
    files: int = 0
    link: str | None = None  # symlink target; links are counted, never followed
    error: str | None = None  # why this directory could only be read partially
    children: list[Node] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Problem:
    path: str
    message: str

    @classmethod
    def of(cls, error: OSError) -> Problem:
        return cls(str(error.filename), error.strerror or str(error))


@dataclass(slots=True)
class Scan:
    root: Node
    problems: list[Problem]


def usage(st: os.stat_result, *, apparent: bool) -> int:
    """Bytes a file accounts for. ``du`` counts allocated blocks, so sparse files are cheap."""
    if apparent or sys.platform == "win32":
        return st.st_size
    return st.st_blocks * 512  # POSIX st_blocks is in 512-byte units, whatever the fs block size


def first_sighting(st: os.stat_result, seen: set[tuple[int, int]]) -> bool:
    """False for the 2nd, 3rd ... name of a hard-linked file: its bytes exist only once."""
    if st.st_nlink < 2 or stat.S_ISDIR(st.st_mode):  # every directory has nlink >= 2
        return True
    key = (st.st_dev, st.st_ino)
    if key in seen:
        return False
    seen.add(key)
    return True


def excluded(name: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(name, pattern) for pattern in patterns)


def scan(root: Path, options: Options = DEFAULTS) -> Scan:
    """Size every entry under ``root``. Unreadable entries become ``Problem``s, not exceptions.

    Raises ``OSError`` only when ``root`` itself can't be stat'ed.
    """
    problems: list[Problem] = []
    seen: set[tuple[int, int]] = set()
    top = root.lstat()

    def visit(path: str, name: str, st: os.stat_result) -> Node:
        own = Size(usage(st, apparent=options.apparent) if first_sighting(st, seen) else 0)
        if stat.S_ISLNK(st.st_mode):
            try:
                target = os.readlink(path)
            except OSError as e:
                target = f"? ({e.strerror})"
            return Node(name, own, files=1, link=target)
        if not stat.S_ISDIR(st.st_mode):
            return Node(name, own, files=1)

        node = Node(name, own, is_dir=True)
        try:
            with os.scandir(path) as entries:  # `with` closes the OS handle even on error
                for entry in entries:
                    if excluded(entry.name, options.exclude):
                        continue
                    try:
                        # Cached on the DirEntry; on Windows it came free with the listing.
                        child = entry.stat(follow_symlinks=False)
                    except OSError as e:
                        problems.append(Problem.of(e))
                        continue
                    if options.one_file_system and child.st_dev != top.st_dev:
                        continue
                    node.children.append(visit(entry.path, entry.name, child))
        except OSError as e:  # PermissionError on open, or an I/O error mid-listing
            node.error = e.strerror
            problems.append(Problem.of(e))

        node.size += sum(c.size for c in node.children)
        node.files = sum(c.files for c in node.children)
        node.children.sort(key=lambda c: (-c.size, c.name))
        return node

    return Scan(visit(os.fspath(root), str(root), top), problems)
