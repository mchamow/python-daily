"""Finding Markdown files, and rewriting them in place without damaging them.

"In place" here means: same path, same permissions, same line endings, and never a
half-written file. The bytes only change when the content does.
"""

import os
import shutil
import tempfile
from collections.abc import Iterable, Iterator
from pathlib import Path

SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__"}


def markdown_files(paths: Iterable[Path]) -> Iterator[Path]:
    """Yield the given files, and every `*.md` under the given directories."""
    for path in paths:
        if path.is_dir():
            yield from (
                p
                for p in sorted(path.rglob("*.md"))
                if not SKIP_DIRS.intersection(p.relative_to(path).parts)
            )
        else:
            yield path  # a missing file fails later, in read_text, with a proper message


def read_text(path: Path) -> str:
    # newline="" turns off universal-newline translation, so a CRLF file reads as CRLF.
    # The default would hand us "\n" and, on Windows, write "\r\n" back: a whole-file diff.
    return path.read_text(encoding="utf-8", newline="")


def write_text(path: Path, text: str) -> None:
    """Replace `path` atomically: a reader sees the old file or the new one, never half."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        shutil.copymode(path, tmp)  # mkstemp creates 0600; keep the original's permissions
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
