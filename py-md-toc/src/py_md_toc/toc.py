"""Render a table of contents and splice it into a document.

Everything here is pure: text in, text out. Reading and writing files is `files.py`'s job, so
the same `update` runs on a file, on stdin, or on a string in a test.
"""

import difflib
import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from urllib.parse import unquote

from .markdown import Heading, Marker, anchor_links, blocks
from .slugs import unique_slugs

OPEN, CLOSE = "<!-- toc -->", "<!-- /toc -->"
# A link inside a TOC entry would be a link inside a link, so links collapse to their text.
LINK = re.compile(r"!?\[(?P<label>[^\]]*)\](?:\([^)]*\)|\[[^\]]*\])?")


class TocError(Exception):
    """The document's TOC markers don't make sense. Carries the 1-based line number."""

    def __init__(self, line: int, message: str) -> None:
        super().__init__(message)
        self.line = line


@dataclass(frozen=True, slots=True)
class BrokenLink:
    anchor: str
    line: int  # 1-based, for messages
    suggestion: str | None


@dataclass(frozen=True, slots=True)
class Update:
    before: str
    after: str
    entries: int
    broken: list[BrokenLink]

    @property
    def changed(self) -> bool:
        return self.before != self.after


def render(heads: Sequence[Heading], slugs: Sequence[str], levels: range) -> list[str]:
    """One nested bullet per heading in `levels`, indented relative to the shallowest one."""
    picked = [(h, s) for h, s in zip(heads, slugs, strict=True) if h.level in levels]
    if not picked:
        return []
    top = min(h.level for h, _ in picked)
    return [
        f"{'  ' * (h.level - top)}- [{LINK.sub(r'\g<label>', h.text)}](#{slug})"
        for h, slug in picked
    ]


def find_block(found: Sequence[Heading | Marker]) -> tuple[int, int] | None:
    """Line indexes of the open and close markers, or None if the document has neither."""
    markers = [b for b in found if isinstance(b, Marker)]
    match markers:
        case []:
            return None
        case [Marker("open", start), Marker("close", end)]:
            return start, end
        case [Marker("open", start)]:
            raise TocError(start + 1, f"{OPEN} has no matching {CLOSE}")
        case [Marker("close", line), *_]:
            raise TocError(line + 1, f"{CLOSE} without an {OPEN} before it")
        case [Marker("open"), Marker("open", line), *_]:
            raise TocError(line + 1, f"a second {OPEN} before {CLOSE}")
        case _:
            raise TocError(markers[2].line + 1, "only one TOC per file is supported")


def update(text: str, levels: range = range(2, 4)) -> Update:
    """Return `text` with an up-to-date TOC, and any in-page links that lead nowhere."""
    newline = "\r\n" if "\r\n" in text else "\n"
    # split(), not splitlines(): splitlines() also breaks on \f, \x1c and U+2028, which would
    # silently rewrite those characters as newlines when the file is joined back together.
    lines = text.split(newline)
    if lines[-1] == "":
        lines.pop()  # the file ended with a newline

    found = list(blocks(lines))
    heads = [b for b in found if isinstance(b, Heading)]
    # Slugs are numbered across *all* headings, including the ones the TOC leaves out.
    slugs = list(unique_slugs(h.text for h in heads))
    toc = render(heads, slugs, levels)

    match find_block(found):
        case (start, end):
            lines[start + 1 : end] = toc
        case None if toc:
            # No markers yet: insert just above the first heading that the TOC lists.
            first = next(h.line for h in heads if h.level in levels)
            lines[first:first] = [OPEN, *toc, CLOSE, ""]
        case None:
            pass  # nothing to list and nowhere it was asked for

    after = newline.join(lines) + (newline if text.endswith(("\n", "\r")) else "")
    return Update(text, after, len(toc), list(check_links(lines, set(slugs))))


def check_links(lines: Sequence[str], slugs: set[str]) -> Iterator[BrokenLink]:
    """Yield `#anchor` links that match no heading, with the closest real anchor."""
    for link in anchor_links(lines):
        anchor = unquote(link.anchor)  # [x](#%C5%82%C3%B3d%C5%BA) is a valid link to #łódź
        if anchor and anchor not in slugs:
            close = difflib.get_close_matches(anchor, slugs, n=1)
            yield BrokenLink(link.anchor, link.line + 1, close[0] if close else None)
