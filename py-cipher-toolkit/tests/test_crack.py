from collections.abc import Callable
from pathlib import Path

import pytest

from py_cipher_toolkit import main
from py_cipher_toolkit.analysis import ENGLISH_IOC, RANDOM_IOC, index_of_coincidence, letters_only
from py_cipher_toolkit.ciphers import atbash, caesar, vigenere
from py_cipher_toolkit.crack import crack, likely_key_length

DATA = Path(__file__).parents[1] / "data"


@pytest.fixture(scope="module")
def message() -> str:
    return (DATA / "message.txt").read_text(encoding="utf-8")


def test_index_of_coincidence_tells_english_from_noise(message: str) -> None:
    assert index_of_coincidence(letters_only(message)) == pytest.approx(ENGLISH_IOC, abs=0.008)
    assert index_of_coincidence("abcdefghijklmnopqrstuvwxyz" * 20) == pytest.approx(
        RANDOM_IOC, abs=0.002
    )
    # A Caesar shift relabels letters but keeps their counts, so the IoC can't see it.
    shifted = letters_only(caesar(message, 11))
    assert index_of_coincidence(shifted) == index_of_coincidence(letters_only(message))


@pytest.mark.parametrize(
    ("encrypt", "cipher", "key"),
    [
        (lambda t: caesar(t, 19), "caesar", "T"),
        (lambda t: vigenere(t, "WALRUS"), "vigenere", "WALRUS"),
        (lambda t: vigenere(t, "Cryptography"), "vigenere", "CRYPTOGRAPHY"),
        (atbash, "atbash", ""),
        (lambda t: t, "caesar", "A"),  # plain English: shift 0
    ],
)
def test_crack_recovers_cipher_and_key(
    message: str, encrypt: Callable[[str], str], cipher: str, key: str
) -> None:
    best = crack(encrypt(message)).best
    assert (best.cipher, best.key) == (cipher, key)
    assert best.plaintext == message


def test_the_shortest_strong_key_length_wins_over_its_multiples() -> None:
    # 18 scores best, but 6 and 12 are within 10% of it: 6 is the key, 12 and 18 its multiples.
    scores = {1: 0.042, 3: 0.053, 6: 0.068, 9: 0.054, 12: 0.068, 18: 0.070}
    assert likely_key_length(scores) == 6


def test_crack_needs_letters() -> None:
    with pytest.raises(ValueError, match="no letters"):
        crack("1234 !!")


def test_cli_round_trip_through_files_and_stdin(
    message: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = tmp_path / "secret.txt"
    main(["vigenere", "-k", "walrus", "-f", str(DATA / "message.txt")])
    secret.write_text(capsys.readouterr().out, encoding="utf-8")

    main(["vigenere", "-d", "-k", "WALRUS", "-f", str(secret)])
    assert capsys.readouterr().out == message

    monkeypatch.setattr("sys.stdin", secret.open(encoding="utf-8"))
    main(["crack"])
    assert capsys.readouterr().out.startswith("Best guess: Vigenère, key WALRUS")


def test_cli_reports_a_bad_key_as_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_:
        main(["vigenere", "-k", "s3cret", "hello"])
    assert exit_.value.code == 2
    assert "ASCII letters only" in capsys.readouterr().err
