"""Heading text → GitHub-compatible anchor slugs.

GitHub builds a heading's `id` from its *rendered* text: lowercase it, drop every character that
isn't a letter, digit, `_`, `-` or space, then turn each space into a hyphen. Repeats get `-1`,
`-2`, … in document order. Matching that exactly is what makes the TOC links work.
"""

import re
from collections.abc import Iterable, Iterator

# One alternative per inline construct, each with its own named group. re.sub scans left to
# right and never rescans a replacement, so whatever sits inside `code` stays untouched.
INLINE = re.compile(
    r"""
      `+ (?P<code> .+? ) `+                          # `List<int>` -> List<int>
    | !?\[ (?P<link> [^\]]* ) \] (?: \( [^)]* \) )?  # [text](url), ![alt](src), [ref] -> text
    | < /? [A-Za-z][^>]* >                           # <kbd>, </b> -> nothing (no group)
    | \\ (?P<escaped> [^\w\s] )                      # \_ -> _
    | (?<![\w\\]) (?P<marks> _{1,3} ) (?P<em> \S (?:.*?\S)? ) (?P=marks) (?!\w)  # _em_ -> em
    """,
    re.VERBOSE,
)

# \w is Unicode-aware for str patterns: Zoë, Łódź and 東京 all survive, emoji and · don't.
NOT_SLUG_CHAR = re.compile(r"[^\w\- ]")


def plain_text(markdown: str) -> str:
    """Approximate the text GitHub renders for a heading's inline Markdown."""

    def keep_text(m: re.Match[str]) -> str:
        # lastgroup names the last group that closed: exactly one per alternative, or None
        # for the tag alternative, which has no group because tags vanish entirely.
        match m.lastgroup:
            case None:
                return ""
            case group:
                return m[group]

    return INLINE.sub(keep_text, markdown)


def slugify(heading: str) -> str:
    """`### `brew --ratio` & friends` → `brew---ratio--friends`, as GitHub does it."""
    # lower(), not casefold(): GitHub keeps ß as ß, while casefold() would turn it into ss.
    text = plain_text(heading).strip().lower()
    return NOT_SLUG_CHAR.sub("", text).replace(" ", "-")


def unique_slugs(headings: Iterable[str]) -> Iterator[str]:
    """Slug each heading in document order, numbering repeats the way github-slugger does.

    Generated slugs are reserved too, so `Example`, `Example`, `Example 1` gives
    `example`, `example-1`, `example-1-1`.
    """
    counts: dict[str, int] = {}
    for heading in headings:
        base = slug = slugify(heading)
        while slug in counts:
            counts[base] += 1
            slug = f"{base}-{counts[base]}"
        counts[slug] = 0
        yield slug
