"""Just enough Markdown parsing to find headings, TOC markers and in-page links.

The parsing is a pipeline of generators. `prose` drops front matter and fenced code, and
`blocks` turns what's left into headings and markers. Nothing is read until somebody iterates,
and each stage only ever holds one line (plus the previous one, for setext headings).
"""

import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Literal

# In VERBOSE mode an unescaped # starts a comment, so the ATX hashes are written as [#].
ATX = re.compile(
    r"""
    ^ [ ]{0,3} (?P<hashes> [#]{1,6} )   # up to 3 spaces of indent; 4 would be a code block
    (?: [ \t]+ (?P<text> .*? ) )?       # the text needs a space first: #hashtag isn't a heading
    (?: [ \t]+ [#]+ )? [ \t]* $         # an optional closing run: ## Title ##
    """,
    re.VERBOSE,
)
SETEXT = re.compile(r"^ {0,3}(?P<underline>=+|-+)[ \t]*$")
FENCE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
MARKER = re.compile(r"^\s*<!--\s*(?P<kind>toc|/toc|tocstop)\s*-->\s*$", re.IGNORECASE)
# Lines that can't be the text of a setext heading: lists, quotes, tables, HTML.
NOT_PARAGRAPH = re.compile(r"^\s*(?:[-*+>|<]|\d+[.)](?:\s|$))")
CODE_SPAN = re.compile(r"(`+).+?\1")
ANCHOR_LINK = re.compile(r"\]\(#(?P<anchor>[^)\s]*)\)")


@dataclass(frozen=True, slots=True)
class Heading:
    level: int
    text: str  # inline Markdown, as written
    line: int  # 0-based index into the document's lines


@dataclass(frozen=True, slots=True)
class Marker:
    kind: Literal["open", "close"]
    line: int


@dataclass(frozen=True, slots=True)
class AnchorLink:
    anchor: str
    line: int


def prose(lines: Sequence[str]) -> Iterator[tuple[int, str]]:
    """Yield `(index, line)` for every line outside YAML front matter and fenced code."""
    start = 0
    if lines and lines[0].rstrip() == "---":  # Jekyll / Hugo front matter
        closing = next((i for i, s in enumerate(lines[1:], 1) if s.rstrip() == "---"), None)
        start = closing + 1 if closing is not None else 0

    fence: str | None = None
    for i, line in enumerate(lines[start:], start):
        m = FENCE.match(line)
        if fence is None:
            if m:
                fence = m["fence"]
            else:
                yield i, line
        # A fence closes with the same character, at least as long, and nothing after it.
        # startswith() checks both at once: "````" closes "```", "~~~~" doesn't.
        elif m and m["fence"].startswith(fence) and not m["info"].strip():
            fence = None


def blocks(lines: Sequence[str]) -> Iterator[Heading | Marker]:
    """Yield headings (ATX and setext) and TOC markers, in document order."""
    previous: tuple[int, str] | None = None  # the last line that could be setext heading text
    for i, line in prose(lines):
        if m := MARKER.match(line):
            yield Marker("open" if m["kind"].lower() == "toc" else "close", i)
        elif m := ATX.match(line):
            yield Heading(len(m["hashes"]), (m["text"] or "").strip(), i)
        elif (m := SETEXT.match(line)) and previous and previous[0] == i - 1:
            level = 1 if m["underline"][0] == "=" else 2
            yield Heading(level, previous[1].strip(), previous[0])
        else:
            is_text = line.strip() and not NOT_PARAGRAPH.match(line)
            previous = (i, line) if is_text else None
            continue
        previous = None  # a heading, marker or underline can't start a setext heading


def headings(lines: Sequence[str]) -> list[Heading]:
    return [b for b in blocks(lines) if isinstance(b, Heading)]


def anchor_links(lines: Sequence[str]) -> Iterator[AnchorLink]:
    """Yield every `[text](#anchor)` link outside code."""
    for i, line in prose(lines):
        for m in ANCHOR_LINK.finditer(CODE_SPAN.sub("", line)):
            yield AnchorLink(m["anchor"], i)
