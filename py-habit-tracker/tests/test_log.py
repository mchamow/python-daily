from datetime import date
from pathlib import Path

import pytest

from py_habit_tracker import main
from py_habit_tracker.log import LogError, add_habit, check_in, load, undo
from py_habit_tracker.render import pad, plain, wants_colour, width
from py_habit_tracker.schedule import parse_schedule


def test_the_log_is_plain_text_that_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "habits.log"
    log = load(path)  # a missing file is an empty log
    run = add_habit(log, "Run", parse_schedule("daily"), date(2026, 11, 1))
    for day in (1, 2, 2, 3):
        check_in(log, run, date(2026, 11, day))  # the second 2 is a no-op
    assert path.read_text() == (
        "habit run daily 2026-11-01\n2026-11-01 run\n2026-11-02 run\n2026-11-03 run\n"
    )

    path.write_text(path.read_text() + "2026-11-02 RUN  # entered twice by hand\n")
    log = load(path)
    assert log.done["run"] == {date(2026, 11, d) for d in (1, 2, 3)}
    assert undo(log, log.habit("run"), date(2026, 11, 2))
    assert load(path).done["run"] == {date(2026, 11, 1), date(2026, 11, 3)}
    assert "2026-11-02" not in path.read_text()


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("2026-11-01 run\n", ":1: check-in for 'run' before"),
        ("habit run daily 2026-11-01\n\n2026-13-01 run\n", ":3: month must be in 1..12"),
        ("habit run sometimes 2026-11-01\n", ":1: can't read schedule word 'sometimes'"),
        ("habit run daily\n", ":1: expected `habit NAME SCHEDULE SINCE`"),
    ],
)
def test_bad_lines_are_reported_with_their_line_number(
    tmp_path: Path, text: str, message: str
) -> None:
    path = tmp_path / "habits.log"
    path.write_text(text)
    with pytest.raises(LogError, match=message):
        load(path)


def test_colour_helpers_measure_what_you_see(monkeypatch: pytest.MonkeyPatch) -> None:
    green = "\x1b[38;2;57;211;83m✓\x1b[0m"
    assert (len(green), width(green)) == (22, 1)  # f"{green:<5}" pads by len(), so not at all
    assert plain(pad(green, 5)) == "✓    "
    monkeypatch.setenv("NO_COLOR", "1")
    with Path(__file__).open() as not_a_tty:
        assert not wants_colour("auto", not_a_tty)
        assert wants_colour("always", not_a_tty)


def test_cli_add_done_and_status(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    common = ["-f", str(tmp_path / "habits.log"), "--today", "2026-11-03"]
    main([*common, "add", "read", "--every", "weekdays", "--since", "-14"])
    main([*common, "done", "read", "fri", "mon", "today"])
    out = capsys.readouterr().out
    assert "Tracking read (weekdays) since Tue 20 Oct 2026." in out
    assert out.rstrip().endswith(
        "Streak: 3 days (best 3 days)"
    )  # Fri, Mon, Tue: the weekend is free

    main([*common, "status"])
    row = next(line for line in capsys.readouterr().out.splitlines() if line.startswith("read"))
    assert row.split()[:5] == ["read", "weekdays", "✓", "3", "days"]
