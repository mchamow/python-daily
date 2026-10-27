"""Slugs must match GitHub's anchors exactly, or the TOC links go nowhere."""

import pytest

from py_md_toc.slugs import slugify, unique_slugs


@pytest.mark.parametrize(
    ("heading", "slug"),
    [
        ("Day 005 · Expense Splitter", "day-005--expense-splitter"),  # · goes, both spaces stay
        ("If you wrote this in C# / TypeScript", "if-you-wrote-this-in-c--typescript"),
        ("### 1. Splitting €100 three ways"[4:], "1-splitting-100-three-ways"),
        ("3. `defaultdict(Account)`: the ledger", "3-defaultdictaccount-the-ledger"),
        ("`List<Recipe>` in the API", "listrecipe-in-the-api"),  # <…> inside code isn't a tag
        ("Press <kbd>Ctrl</kbd>+C", "press-ctrlc"),
        ("Brewing a V60 ☕", "brewing-a-v60-"),  # the emoji goes, its space doesn't
        ("Why is it called _Brewbot_?", "why-is-it-called-brewbot"),
        ("snake_case and \\_escaped\\_", "snake_case-and-_escaped_"),
        ("See [the docs](https://example.com) first", "see-the-docs-first"),
        ("Straße in Łódź", "straße-in-łódź"),  # lower(), not casefold()
    ],
)
def test_slugify_matches_github(heading: str, slug: str) -> None:
    assert slugify(heading) == slug


def test_repeats_are_numbered_and_generated_slugs_are_reserved() -> None:
    texts = ["Example", "Example", "Example 1", "Example"]
    assert list(unique_slugs(texts)) == ["example", "example-1", "example-1-1", "example-2"]
