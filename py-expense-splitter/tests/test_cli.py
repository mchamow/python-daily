from pathlib import Path

import pytest

from py_expense_splitter import main

SAMPLE = str(Path(__file__).parent.parent / "data" / "lisbon.csv")


def test_demo_output(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([SAMPLE, "--compare"]) == 0
    out = capsys.readouterr().out
    assert "Lisbon long weekend · 5 people · 13 expenses · €1,337.90" in out
    assert "Settle up in 3 transfers:" in out
    assert "Dee  →  Ben  €177.84" in out
    assert "   4  greedy" in out


def test_floats_leave_a_cent_behind(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([SAMPLE, "--floats", "-c", "$"]) == 0
    out = capsys.readouterr().out
    assert "$1,337.90" in out
    assert "is still owed 0.00999" in out


def test_bad_file_is_a_clean_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(tmp_path / "missing.csv")]) == 1
    assert "split: can't read" in capsys.readouterr().err
