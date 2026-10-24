"""The generators: shape of the output, and that the entropy they claim is exactly right."""

import math
from itertools import product

import pytest

from py_password_meter.generate import AMBIGUOUS, CLASSES, count_valid, passphrase, password
from py_password_meter.wordlists import eff_words


@pytest.mark.parametrize(("length", "sizes"), [(3, [2, 3]), (4, [1, 1, 2]), (5, [2, 2, 1, 1])])
def test_count_valid_matches_brute_force(length: int, sizes: list[int]) -> None:
    # Label every character with its pool number, then count strings that use every pool.
    alphabet = [pool for pool, size in enumerate(sizes) for _ in range(size)]
    expected = sum(set(s) == set(range(len(sizes))) for s in product(alphabet, repeat=length))
    assert count_valid(length, sizes) == expected


def test_password_has_every_class_and_reports_exact_bits() -> None:
    for _ in range(50):
        secret = password(8)
        assert len(secret.text) == 8
        assert all(set(chars) & set(secret.text) for chars in CLASSES.values())
    # 94**8 strings minus those missing a class: a bit under 8 * log2(94).
    assert secret.bits == pytest.approx(math.log2(count_valid(8, [26, 26, 10, 32])))
    assert secret.bits < 8 * math.log2(94)

    unambiguous = "".join(password(64, unambiguous=True).text for _ in range(20))
    assert AMBIGUOUS.isdisjoint(unambiguous)


@pytest.mark.parametrize(
    ("length", "classes", "message"),
    [(3, tuple(CLASSES), "can't fit"), (10, (), "at least one")],
)
def test_password_rejects_impossible_requests(
    length: int, classes: tuple[str, ...], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        password(length, classes)


def test_passphrase_words_come_from_the_list() -> None:
    secret = passphrase(5, separator=" ", capitalize=True)
    words = secret.text.split(" ")
    assert len(words) == 5
    assert all(word.lower() in eff_words() for word in words)
    # Capitalising is a fixed rule: it adds no entropy.
    assert secret.bits == pytest.approx(5 * math.log2(7776))

    # A digit on one of 4 words: 10 digits times 4 places.
    secret = passphrase(4, number=True)
    assert sum(char.isdigit() for char in secret.text) == 1
    assert secret.bits == pytest.approx(4 * math.log2(7776) + math.log2(40))
