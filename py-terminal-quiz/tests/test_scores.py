import io
import json
from pathlib import Path

import pytest

from py_terminal_quiz import main, scores
from py_terminal_quiz.scores import Entry, ScoreFileError


def entry(name: str, score: int, seconds: float = 30.0) -> Entry:
    return Entry(name, score, 3, 5, seconds, 42, "2026-10-31")


def test_record_ranks_breaks_ties_on_time_and_keeps_ten() -> None:
    boards: scores.Boards = {}
    assert scores.record(boards, "g", entry("Ola", 3000)) == 1
    assert scores.record(boards, "g", entry("Michał", 3000, seconds=12.5)) == 1  # same, faster
    assert scores.record(boards, "g", entry("Tom", 100)) == 3
    for i in range(10):
        scores.record(boards, "g", entry(f"bot{i}", 2000))
    assert len(boards["g"]) == scores.KEEP
    assert scores.record(boards, "g", entry("late", 50)) is None
    assert [e.name for e in boards["g"][:2]] == ["Michał", "Ola"]
    replay = entry("Michał", 3000, seconds=12.5)
    assert replay == boards["g"][0]  # dataclass equality is by value...
    assert scores.record(boards, "g", replay) == 2  # ...so record() matches by identity


def test_round_trip_through_json(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "scores.json"
    boards: scores.Boards = {"general · 5q": [entry("Michał", 4215)], "python · 3q": []}
    scores.save(path, boards)
    assert scores.load(path) == boards
    text = path.read_text(encoding="utf-8")
    assert '"Michał"' in text  # ensure_ascii=False
    assert list(tmp_path.joinpath("nested").iterdir()) == [path]  # no temp file left behind


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("{not json", "not valid JSON"),
        ('{"version": 2, "boards": {}}', "version 2"),
        ("[1, 2, 3]", "doesn't look like"),
        ('{"version": 1, "boards": {"g": [{"name": "x"}]}}', "malformed entry"),
    ],
)
def test_bad_score_files_are_reported(tmp_path: Path, content: str, message: str) -> None:
    path = tmp_path / "scores.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ScoreFileError, match=message):
        scores.load(path)


def test_main_plays_a_piped_game_and_saves_the_score(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(Path(__file__).parent.parent)  # the default questions file is data/...
    monkeypatch.setattr("sys.stdin", io.StringIO("a\nb\n"))  # two answers, then end of input
    path = tmp_path / "s.json"
    assert main(["--seed", "7", "-n", "3", "--name", "Test", "--scores", str(path)]) == 0
    out = capsys.readouterr().out
    assert "Replay this exact quiz: quiz --seed 7 -n 3" in out
    saved = json.loads(path.read_text(encoding="utf-8"))
    [best] = saved["boards"]["general · 3q"]
    assert (best["name"], best["total"], best["seed"]) == ("Test", 2, 7)
