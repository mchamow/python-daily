"""What counts as a heading, and what only looks like one."""

from textwrap import dedent

from py_md_toc.markdown import Heading, anchor_links, headings


def lines(text: str) -> list[str]:
    return dedent(text).strip("\n").split("\n")


def test_atx_and_setext_headings() -> None:
    doc = lines("""
        # Title
        ## Closed ##
        Setext two
        ----------
        Setext one
        ==========
        #hashtag is a paragraph
            ## indented four spaces is code
        - list item
        ---
        """)
    assert headings(doc) == [
        Heading(1, "Title", 0),
        Heading(2, "Closed", 1),
        Heading(2, "Setext two", 2),
        Heading(1, "Setext one", 4),
    ]


def test_fences_and_front_matter_hide_headings() -> None:
    doc = lines("""
        ---
        title: not a setext heading
        ---
        ````md
        # inside a four-backtick fence
        ```
        # still inside: a shorter fence can't close it
        ````
        ~~~
        ## tilde fence
        ~~~
        ## Real
        """)
    assert headings(doc) == [Heading(2, "Real", 11)]


def test_anchor_links_skip_code() -> None:
    doc = lines("""
        See [a](#one) and `[b](#two)`.
        ```
        [c](#three)
        ```
        [d](#four) [e](https://example.com/#five)
        """)
    assert [(link.anchor, link.line) for link in anchor_links(doc)] == [("one", 0), ("four", 4)]
