"""Rendering and splicing the TOC: pure text in, text out."""

from pathlib import Path
from textwrap import dedent

import pytest

from py_md_toc.toc import TocError, update

DATA = Path(__file__).parent.parent / "data"


def doc(text: str) -> str:
    return dedent(text).lstrip("\n")


def test_inserts_above_first_listed_heading() -> None:
    result = update(
        doc("""
        # Title

        Intro.

        ## One
        ### One point five
        #### Too deep
        ## [Two](https://example.com)
        """)
    )
    assert result.after == doc("""
        # Title

        Intro.

        <!-- toc -->
        - [One](#one)
          - [One point five](#one-point-five)
        - [Two](#two)
        <!-- /toc -->

        ## One
        ### One point five
        #### Too deep
        ## [Two](https://example.com)
        """)


def test_refreshes_stale_toc_and_is_idempotent() -> None:
    first = update((DATA / "guide.md").read_text())
    assert first.changed
    assert "- [Old flags]" not in first.after
    assert "  - [Example](#example-2)" in first.after
    second = update(first.after)
    assert not second.changed


def test_levels_and_empty_toc() -> None:
    text = doc("""
        <!-- toc -->
        - [stale](#stale)
        <!-- /toc -->
        # Only a title
        """)
    assert "- [Only a title](#only-a-title)" in update(text, range(1, 2)).after
    assert update(text).after.startswith("<!-- toc -->\n<!-- /toc -->\n")


def test_preserves_crlf_and_missing_final_newline() -> None:
    text = "# T\r\n\r\n## A\r\n\r\nend"
    after = update(text).after
    assert after == "# T\r\n\r\n<!-- toc -->\r\n- [A](#a)\r\n<!-- /toc -->\r\n\r\n## A\r\n\r\nend"


def test_broken_links_get_suggestions() -> None:
    result = update((DATA / "guide.md").read_text())
    assert [(b.anchor, b.suggestion) for b in result.broken] == [("instalation", "installation")]


@pytest.mark.parametrize(
    ("text", "line"),
    [
        ("<!-- toc -->\n## A\n", 1),
        ("<!-- /toc -->\n## A\n", 1),
        ("<!-- toc -->\n<!-- toc -->\n<!-- /toc -->\n", 2),
    ],
)
def test_bad_markers_report_their_line(text: str, line: int) -> None:
    with pytest.raises(TocError) as e:
        update(text)
    assert e.value.line == line
