"""Reading inputs and the command-line behaviour, end to end."""

import io
import json
from pathlib import Path

import pytest

from day_001_word_frequency import main
from day_001_word_frequency.sources import SourceError, iter_sources


@pytest.fixture
def corpus(tmp_path: Path) -> Path:
    (tmp_path / "nested").mkdir()
    (tmp_path / "b.txt").write_text("whale whale whale ship ship sea", encoding="utf-8")
    (tmp_path / "nested" / "a.txt").write_text("rabbit rabbit rabbit tea tea", encoding="utf-8")
    (tmp_path / "notes.md").write_text("ignored by the default *.txt glob", encoding="utf-8")
    return tmp_path


def test_directories_are_searched_recursively_in_sorted_order(corpus: Path) -> None:
    names = [Path(s.name).relative_to(corpus).as_posix() for s in iter_sources([str(corpus)])]
    assert names == ["b.txt", "nested/a.txt"]


def test_dash_reads_stdin() -> None:
    [source] = iter_sources(["-"], stdin=io.StringIO("from a pipe"))
    assert source == source.__class__("<stdin>", "from a pipe")


def test_missing_path_raises_a_readable_error(tmp_path: Path) -> None:
    with pytest.raises(SourceError, match="no such file"):
        list(iter_sources([str(tmp_path / "nope.txt")]))


def test_cli_json_output(corpus: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(corpus), "--json", "-n", "2"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["top"] == [{"word": "whale", "count": 3}, {"word": "rabbit", "count": 3}]
    assert report["words_scanned"] == 11


def test_cli_ignore_adds_stop_words(corpus: Path, capsys: pytest.CaptureFixture[str]) -> None:
    main([str(corpus), "--json", "--ignore", "WHALE"])
    top_words = [row["word"] for row in json.loads(capsys.readouterr().out)["top"]]
    assert "whale" not in top_words


def test_cli_errors_go_to_stderr_with_exit_code_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([str(tmp_path / "missing.txt")]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "wordfreq:" in captured.err
