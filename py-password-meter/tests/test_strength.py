"""The strength meter: matchers, the cheapest-cover search, and how results are presented."""

import math
from pathlib import Path

import pytest

from py_password_meter import main, render_report
from py_password_meter.matchers import keyboard, year
from py_password_meter.strength import estimate, human_duration

SAMPLES = Path(__file__).parent.parent / "data" / "passwords.txt"


@pytest.mark.parametrize(
    ("password", "patterns"),
    [
        ("P@ssw0rd2024!", ["dictionary", "year", "bruteforce"]),
        ("abcabcabcabc", ["repeat"]),
        ("zyxwvu98", ["sequence", "bruteforce"]),
        ("hjkl;'", ["keyboard"]),
        ("Summer2026!", ["dictionary", "year", "bruteforce"]),
    ],
)
def test_weak_passwords_are_seen_through(password: str, patterns: list[str]) -> None:
    est = estimate(password)
    assert [seg.pattern for seg in est.segments] == patterns
    assert "".join(seg.token for seg in est.segments) == password  # segments tile the password
    assert est.rating == "very weak"
    assert est.bits < est.naive_bits / 2


def test_estimate_never_exceeds_the_naive_formula() -> None:
    for line in SAMPLES.read_text(encoding="utf-8").splitlines():
        est = estimate(line)
        assert est.bits <= est.naive_bits + 1e-9, line


def test_random_password_gets_full_credit() -> None:
    est = estimate("kT9#vQ2$wL7!pX4&")
    assert est.bits == pytest.approx(est.naive_bits)
    assert est.guesses == 95**16  # an exact Python int, far beyond 64 bits


def test_passphrase_scores_close_to_its_true_entropy() -> None:
    # Six EFF words joined by '-': 6 * log2(7776), plus a guess at the separator.
    est = estimate("ozone-spinach-blurt-mascot-unpaved-rearview")
    assert est.bits == pytest.approx(6 * math.log2(7776) + math.log2(5))
    assert est.naive_bits > 250  # the naive formula is wildly generous here


def test_years_overlap_and_keyboard_walks_need_three_keys() -> None:
    assert [m.token for m in year("19992000")] == ["1999", "2000"]
    assert [m.token for m in keyboard("xqwe")] == ["qwe"]
    assert list(keyboard("qw")) == []


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0.2, "under a second"),
        (1, "1 second"),
        (90, "2 minutes"),
        (400 * 86400, "1 year"),
        (3.2e10, "1 thousand years"),
        (1e30, "longer than the universe has existed"),
    ],
)
def test_human_duration(seconds: float, expected: str) -> None:
    assert human_duration(seconds) == expected


def test_hidden_report_never_prints_the_password() -> None:
    report = render_report(estimate("Hunter2024"), reveal=False)
    assert "Hunter" not in report
    assert "2024" not in report
    assert "dictionary" in report


def test_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # gen: secrets alone on stdout, commentary on stderr
    assert main(["gen", "-n", "16", "-c", "3"]) == 0
    out, err = capsys.readouterr()
    assert [len(line) for line in out.splitlines()] == [16, 16, 16]
    assert "bits of entropy" in err

    # check --file: several passwords make a table
    passwords = tmp_path / "pw.txt"
    passwords.write_text("password1\nkT9#vQ2$wL7!pX4&\n", encoding="utf-8")
    assert main(["check", "--file", str(passwords)]) == 0
    rows = capsys.readouterr().out.splitlines()
    assert "very weak" in rows[1]
    assert "very strong" in rows[2]
    assert main(["check", "--file", str(tmp_path / "missing.txt")]) == 2
