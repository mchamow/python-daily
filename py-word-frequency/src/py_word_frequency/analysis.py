"""Counting words and finding what makes each document distinctive."""

import heapq
from collections import Counter
from collections.abc import Iterable, Mapping, Set
from dataclasses import dataclass
from operator import attrgetter


def count_words(words: Iterable[str]) -> Counter[str]:
    """Count every word. Counter consumes any iterable, including a lazy generator."""
    return Counter(words)


def filter_counts(
    counts: Counter[str], *, min_length: int = 1, stop_words: Set[str] = frozenset()
) -> Counter[str]:
    """Drop short words and stop words. Filtering the vocabulary, not the token stream,
    means each distinct word is checked once instead of once per occurrence."""
    return Counter(
        {w: n for w, n in counts.items() if len(w) >= min_length and w not in stop_words}
    )


@dataclass(frozen=True, slots=True)
class Distinctive:
    word: str
    count: int
    lift: float  # how many times more frequent here than in the other documents


def distinctive_words(
    per_doc: Mapping[str, Counter[str]], *, top: int = 10, min_count: int = 3
) -> dict[str, list[Distinctive]]:
    """For each document, the words most over-represented compared with all the others.

    Lift = (rate in this document) / (rate in the rest), with add-one smoothing so a
    word that never appears elsewhere doesn't divide by zero.
    """
    if len(per_doc) < 2:
        raise ValueError("distinctive words need at least two documents to compare")

    total: Counter[str] = sum(per_doc.values(), Counter())  # Counter + Counter merges counts
    vocabulary = len(total)
    result: dict[str, list[Distinctive]] = {}
    for name, counts in per_doc.items():
        rest = total - counts  # Counter - Counter subtracts, dropping words that hit zero
        doc_size, rest_size = counts.total(), rest.total()
        scored = (
            Distinctive(
                word,
                n,
                ((n + 1) / (doc_size + vocabulary)) / ((rest[word] + 1) / (rest_size + vocabulary)),
            )
            for word, n in counts.items()
            if n >= min_count
        )
        result[name] = heapq.nlargest(top, scored, key=attrgetter("lift"))
    return result
