"""End to end through main(): files on disk, exit codes, and what gets rewritten."""

import os
import shutil
from pathlib import Path

import pytest

from py_md_toc import main

DATA = Path(__file__).parent.parent / "data"


@pytest.fixture
def docs(tmp_path: Path) -> Path:
    shutil.copytree(DATA, tmp_path / "docs")
    (tmp_path / "docs" / "broken.md").unlink()
    return tmp_path / "docs"


def test_check_fails_then_update_fixes_toc(docs: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--check", str(docs)]) == 1
    assert main([str(docs)]) == 0
    assert "updated" in capsys.readouterr().out
    (docs / "guide.md").write_text(
        (docs / "guide.md").read_text().replace("#instalation", "#installation")
    )
    assert main(["--check", str(docs)]) == 0


def test_rewrite_keeps_mode_and_skips_unchanged_files(docs: Path) -> None:
    guide, changelog = docs / "guide.md", docs / "changelog.md"
    guide.chmod(0o640)
    main([str(docs)])
    assert guide.stat().st_mode & 0o777 == 0o640
    os.utime(changelog, (0, 0))  # a second run must not touch an up-to-date file
    main([str(docs)])
    assert changelog.stat().st_mtime == 0
    assert not list(docs.glob(".*.tmp"))


def test_bad_markers_exit_2(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--check", str(DATA / "broken.md")]) == 2
    assert "broken.md:3: <!-- toc --> has no matching <!-- /toc -->" in capsys.readouterr().err
