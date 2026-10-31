"""High scores in a JSON file: one top-10 board per quiz setup ("general · 5q", ...).

The file looks like::

    {"version": 1, "boards": {"general · 5q": [{"name": "Michał", "score": 4215, ...}]}}
"""

import json
import os
import tempfile
from dataclasses import asdict, dataclass, fields
from pathlib import Path

VERSION = 1
KEEP = 10

type Seed = int | str
type Boards = dict[str, list[Entry]]


class ScoreFileError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class Entry:
    name: str
    score: int
    correct: int
    total: int
    seconds: float  # total time spent answering
    seed: Seed
    played: str  # ISO 8601 date; JSON has no date type

    def rank_key(self) -> tuple[int, float, str]:
        return (-self.score, self.seconds, self.played)  # ties: faster, then earlier, wins


def load(path: Path) -> Boards:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}  # nobody has played yet
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ScoreFileError(f"{path} is not valid JSON ({error})") from error
    match raw:
        case {"version": 1, "boards": dict(boards)}:
            pass
        case {"version": int(other)}:
            raise ScoreFileError(f"{path} is version {other}; this quiz reads {VERSION}")
        case _:
            raise ScoreFileError(f"{path} doesn't look like a quiz score file")
    names = {f.name for f in fields(Entry)}
    try:
        # Entry(**d) is the whole decoder: keys become keyword arguments. Filtering on names
        # keeps an older quiz from choking on a field a newer one added.
        return {
            key: [Entry(**{k: v for k, v in d.items() if k in names}) for d in entries]
            for key, entries in boards.items()
        }
    except (TypeError, AttributeError) as error:  # a missing field, or an entry that isn't a dict
        raise ScoreFileError(f"{path} has a malformed entry ({error})") from error


def save(path: Path, boards: Boards) -> None:
    """Atomic write, as on day 4: temp file in the same directory, then os.replace."""
    data = {"version": VERSION, "boards": {k: [asdict(e) for e in v] for k, v in boards.items()}}
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as tmp:
        # ensure_ascii=False writes "Michał" rather than "Micha\u0142".
        json.dump(data, tmp, indent=2, ensure_ascii=False)
        tmp.write("\n")
    try:
        os.replace(tmp.name, path)
    except BaseException:
        os.unlink(tmp.name)
        raise


def record(boards: Boards, key: str, entry: Entry) -> int | None:
    """Add ``entry`` to its board; return its 1-based rank, or None if it didn't make the cut."""
    board = sorted([*boards.get(key, []), entry], key=Entry.rank_key)
    boards[key] = board[:KEEP]
    # Identity, not ==: a frozen dataclass compares by value, and a replay can tie exactly.
    return next((i for i, e in enumerate(boards[key], start=1) if e is entry), None)


def render(boards: Boards, key: str | None = None, *, highlight: Entry | None = None) -> str:
    keys = [key] if key else sorted(boards)
    if not any(boards.get(k) for k in keys):
        return "No high scores yet."
    out: list[str] = []
    for k in keys:
        out.append(f"\n🏆 {k}")
        for i, e in enumerate(boards.get(k, []), start=1):
            mark = "  ← you" if e is highlight else ""
            out.append(
                f"{i:>3}. {e.name:<12} {e.score:>7,}  {e.correct}/{e.total}  "
                f"{e.seconds:>5.1f}s  {e.played}  seed {e.seed}{mark}"
            )
    return "\n".join(out).lstrip("\n")
