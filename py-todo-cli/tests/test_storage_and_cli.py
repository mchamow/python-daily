"""Storage guarantees (atomic, locked, all-or-nothing) and the CLI on top of them."""

import os
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import pytest

from py_todo_cli import main
from py_todo_cli.race import race
from py_todo_cli.storage import StorageError, editing, load, save


@pytest.fixture
def path(tmp_path: Path) -> Path:
    return tmp_path / "todo.json"


def _add(path: Path, title: str) -> None:
    with editing(path) as todo:
        todo.add(title, now=datetime.now(UTC))


def test_failed_save_leaves_the_old_file_and_no_temp_files(
    path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _add(path, "keep me")
    before = path.read_bytes()

    def crash(src: str, dst: str) -> None:
        raise OSError("disk unplugged")

    monkeypatch.setattr(os, "replace", crash)
    todo = load(path)
    todo.add("lost", now=datetime.now(UTC))
    with pytest.raises(OSError, match="unplugged"):
        save(path, todo)
    assert path.read_bytes() == before
    assert sorted(p.name for p in path.parent.iterdir()) == ["todo.json", "todo.json.lock"]


def test_concurrent_writers_lose_nothing(path: Path) -> None:
    kept, crashes, state = race(path, safe=True, writers=64)
    assert (kept, crashes, state) == (64, Counter(), "valid JSON")
    assert sorted(t.id for t in load(path).tasks) == list(range(1, 65))


@pytest.mark.parametrize(
    ("content", "message"),
    [("{not json", "not valid JSON"), ('{"version": 2}', "version 2; this todo reads 1")],
)
def test_load_refuses_bad_files(path: Path, content: str, message: str) -> None:
    path.write_text(content, encoding="utf-8")
    with pytest.raises(StorageError, match=message):
        load(path)


def test_cli_flow(path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    def run(*argv: str) -> tuple[int, str]:
        code = main(list(argv))
        out, err = capsys.readouterr()
        return code, out + err

    # -f works before or after the subcommand
    assert run("-f", str(path), "add", "Buy", "milk", "-t", "home", "--due", "today")[0] == 0
    assert run("add", "Renew passport", "-p", "high", "-f", str(path))[0] == 0
    _, out = run("-f", str(path), "list")
    assert out.splitlines()[0].startswith("[ ]  #2  high")  # high priority sorts first
    assert "Buy milk #home" in out

    # all or nothing: #1 exists, #9 doesn't, so #1 must stay open
    assert run("-f", str(path), "done", "1", "9") == (1, "todo: no task #9\n")
    assert not load(path).find(1).done

    assert run("-f", str(path), "done", "1")[0] == 0
    _, out = run("-f", str(path), "ls")
    assert "Buy milk" not in out
    assert "(+1 done" in out
    assert run("-f", str(path), "rm", "2")[1] == "removed #2: Renew passport\n"
    assert run("-f", str(path), "clear")[1] == "cleared 1 done task(s)\n"
    assert load(path).tasks == []
    assert load(path).next_id == 3  # ids are never reused
