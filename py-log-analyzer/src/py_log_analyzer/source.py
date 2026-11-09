"""Where lines come from: plain or compressed files and stdin, chained into one lazy stream.

Rotated logs arrive as `access.log`, `access.log.1.gz`, `access.log.2.zst` and so on. The format
is sniffed from the first bytes (not the file extension), so a renamed file still opens.
"""

import io
import sys
from collections.abc import Iterable, Iterator

# Python 3.14 groups the compressors under `compression.*`, and adds Zstandard to the stdlib.
from compression import bz2, gzip, lzma, zstd
from contextlib import AbstractContextManager, nullcontext
from pathlib import Path
from typing import Literal, NamedTuple, TextIO

type Codec = Literal["gzip", "bzip2", "xz", "zstd", "plain"]

_MAGIC: dict[bytes, Codec] = {
    b"\x1f\x8b": "gzip",
    b"BZh": "bzip2",
    b"\xfd7zXZ\x00": "xz",
    b"\x28\xb5\x2f\xfd": "zstd",
}

# A user agent can contain any bytes at all. Crashing on line 3,141,592 of a 2 GB log because of
# one bad byte is worse than showing it escaped as \xff.
ERRORS = "backslashreplace"


class Line(NamedTuple):
    """One raw line and where it came from (for error messages)."""

    source: str
    number: int
    text: str


def sniff(path: Path) -> Codec:
    with path.open("rb") as raw:
        head = raw.read(6)
    return next((codec for magic, codec in _MAGIC.items() if head.startswith(magic)), "plain")


def open_log(path: Path) -> TextIO:
    """Open a log for reading as text, decompressing on the fly. Nothing is read up front."""
    match sniff(path):
        case "gzip":
            return gzip.open(path, "rt", encoding="utf-8", errors=ERRORS)
        case "bzip2":
            return bz2.open(path, "rt", encoding="utf-8", errors=ERRORS)
        case "xz":
            return lzma.open(path, "rt", encoding="utf-8", errors=ERRORS)
        case "zstd":
            return zstd.open(path, "rt", encoding="utf-8", errors=ERRORS)
        case "plain":
            return path.open(encoding="utf-8", errors=ERRORS)


def _open(source: str) -> AbstractContextManager[TextIO]:
    if source == "-":
        if isinstance(sys.stdin, io.TextIOWrapper):
            sys.stdin.reconfigure(encoding="utf-8", errors=ERRORS)
        return nullcontext(sys.stdin)  # read stdin, but never close it
    return open_log(Path(source))


def read_lines(sources: Iterable[str]) -> Iterator[Line]:
    """Every line of every source, in order. One file is open at a time."""
    for source in sources:
        with _open(source) as stream:
            for number, text in enumerate(stream, start=1):
                yield Line(source, number, text)
