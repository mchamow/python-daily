"""End to end through main(), on the bundled sample tree."""

import re
from pathlib import Path

import pytest

from py_disk_usage import main

SAMPLE = Path(__file__).parent.parent / "data" / "sample"


def test_tree_and_largest_on_sample(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(SAMPLE), "-A", "-d", "1"]) == 0
    out = capsys.readouterr().out
    assert "sample/  (14 files)" in out
    assert "└── latest.log -> logs/app.log" in out
    # Directory sizes are filesystem metadata, so check the shape rather than exact bytes.
    assert re.search(r"\n18\d,\d{3} bytes apparent size · scanned in \d+\.\d\ds\n$", out)

    assert main([str(SAMPLE), "-A", "-l", "2", "-e", "logs", "--si"]) == 0
    first, second = capsys.readouterr().out.splitlines()[:2]
    assert first.endswith("kB  assets/fonts/Brew-Bold.woff2")
    assert second.endswith("assets/fonts/Brew-Regular.woff2")


def test_missing_path_exits_2(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    assert main([str(tmp_path / "nope")]) == 2
    assert "no such file or directory" in capsys.readouterr().err
