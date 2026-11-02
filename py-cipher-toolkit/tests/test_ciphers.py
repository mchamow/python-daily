import pytest

from py_cipher_toolkit.ciphers import atbash, caesar, shortest_period, vigenere


def test_caesar_keeps_case_punctuation_and_non_ascii_letters() -> None:
    assert caesar("Hello, World! Zażółć 42", 3) == "Khoor, Zruog! Cdżółć 42"


@pytest.mark.parametrize("shift", [0, 1, 13, 25, 26, -3, 1_000_003])
def test_caesar_round_trips_for_any_int_shift(shift: int) -> None:
    text = "The quick brown fox jumps over the lazy dog."
    assert caesar(caesar(text, shift), -shift) == text
    assert caesar(text, shift) == caesar(text, shift % 26)  # -3 and 23 are the same shift


def test_vigenere_textbook_vector_and_the_key_skips_non_letters() -> None:
    assert vigenere("ATTACKATDAWN", "LEMON") == "LXFOPVEFRNHR"
    assert vigenere("Attack at dawn!", "lemon") == "Lxfopv ef rnhr!"
    assert vigenere("Lxfopv ef rnhr!", "LEMON", decrypt=True) == "Attack at dawn!"


@pytest.mark.parametrize("key", ["", "two words", "klucz-ł", "123"])
def test_vigenere_rejects_keys_that_are_not_ascii_letters(key: str) -> None:
    with pytest.raises(ValueError, match="ASCII letters"):
        vigenere("anything", key)


def test_atbash_is_its_own_inverse() -> None:
    assert atbash("Wizard") == "Draziw"  # a famous fluke: "wizard" mirrors to itself reversed
    assert atbash(atbash("Any text, at all.")) == "Any text, at all."


@pytest.mark.parametrize(
    ("key", "period"),
    [("WALRUSWALRUS", "WALRUS"), ("AAAA", "A"), ("ABAB", "AB"), ("ABA", "ABA"), ("Q", "Q")],
)
def test_shortest_period(key: str, period: str) -> None:
    assert shortest_period(key) == period
