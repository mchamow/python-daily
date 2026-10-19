"""Tokenising, counting, filtering and the distinctive-words score."""

from collections import Counter

import pytest

from py_word_frequency.analysis import count_words, distinctive_words, filter_counts
from py_word_frequency.text import STOP_WORDS, words


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Hello, hello WORLD!", ["hello", "hello", "world"]),
        (
            "Don\N{RIGHT SINGLE QUOTATION MARK}t panic: don't",
            ["don't", "panic", "don't"],
        ),  # curly and straight apostrophes merge
        ("It's 4 o'clock", ["it's", "o'clock"]),  # digits are not words
        ("Café STRASSE Straße", ["café", "strasse", "strasse"]),  # casefold, not lower
        ("snake_case and 'quoted'", ["snake", "case", "and", "quoted"]),
    ],
    ids=["case", "apostrophes", "digits", "unicode", "punctuation"],
)
def test_words_normalises_tokens(text: str, expected: list[str]) -> None:
    assert list(words(text)) == expected


def test_words_is_lazy() -> None:
    tokens = words("one two three")
    assert next(tokens) == "one"  # a generator: nothing past "one" has been scanned yet


def test_filter_counts_drops_stop_words_and_short_words() -> None:
    counts = count_words(words("The whale and the sea. A whale is big, ok?"))
    kept = filter_counts(counts, min_length=3, stop_words=STOP_WORDS)
    assert kept == Counter({"whale": 2, "sea": 1, "big": 1})


def test_counters_merge_with_plus() -> None:
    a, b = Counter({"whale": 2, "sea": 1}), Counter({"whale": 1, "ship": 4})
    assert sum([a, b], Counter()) == Counter({"ship": 4, "whale": 3, "sea": 1})


def test_distinctive_ranks_document_specific_words_first() -> None:
    per_doc = {
        "alice": Counter({"alice": 10, "rabbit": 5, "said": 20}),
        "moby": Counter({"whale": 12, "ship": 6, "said": 22}),
    }
    result = distinctive_words(per_doc, top=2)
    assert [d.word for d in result["alice"]] == ["alice", "rabbit"]
    assert [d.word for d in result["moby"]] == ["whale", "ship"]
    assert all(d.lift > 1 for items in result.values() for d in items)


def test_distinctive_needs_two_documents() -> None:
    with pytest.raises(ValueError, match="at least two"):
        distinctive_words({"only": Counter({"word": 5})})
