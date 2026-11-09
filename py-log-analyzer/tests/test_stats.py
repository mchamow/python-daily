from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from py_log_analyzer import main
from py_log_analyzer.parse import Request
from py_log_analyzer.stats import analyze, incidents

T0 = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)
DATA = Path(__file__).parent.parent / "data"


def req(minute: int, status: int = 200, ms: float | None = 10.0, path: str = "/a") -> Request:
    time = T0 + timedelta(minutes=minute, seconds=7)
    return Request("10.0.0.1", time, "GET", path, status, 100, "", ms)


def test_slowest_keeps_top_n_and_survives_ties() -> None:
    # Equal times would make heapq compare two Requests if the entries had no tie-breaker.
    times = [5.0, 50.0, 50.0, 1.0, 50.0, 70.0, 3.0]
    stats = analyze((req(0, ms=ms) for ms in times), top=3)
    assert [r.ms for r in stats.slowest] == [70.0, 50.0, 50.0]


def test_window_is_min_and_max_even_when_files_are_out_of_order() -> None:
    stats = analyze([req(30), req(5), req(90)])
    assert (stats.first, stats.last) == (req(5).time, req(90).time)


def test_incidents_merge_consecutive_bad_minutes_and_name_the_culprit() -> None:
    traffic = []
    for minute in range(20):
        traffic += [req(minute) for _ in range(40)]
        if minute in (3, 4, 5, 12):  # a 3-minute outage, then one bad minute alone
            traffic += [req(minute, 503, path="/pay") for _ in range(8)]
            traffic += [req(minute, 500, path="/b")]
        elif minute == 15:  # 4 errors: below the threshold of 5
            traffic += [req(minute, 503) for _ in range(4)]
    found = incidents(analyze(traffic).minutes)
    assert [(i.start - T0, i.minutes, i.errors) for i in found] == [
        (timedelta(minutes=3), 3, 27),
        (timedelta(minutes=12), 1, 9),
    ]
    assert (found[0].culprit, found[0].culprit_errors) == ("GET /pay", 24)


def test_cli_finds_the_planted_outage(capsys: pytest.CaptureFixture[str]) -> None:
    files = [str(DATA / name) for name in ("access.log.2.zst", "access.log.1.gz", "access.log")]
    assert main([*files, "--since", "2026-11-08T12:00+01:00", "--until", "2026-11-08T16:00"]) == 0
    out = capsys.readouterr().out
    assert "2026-11-08 14:07 → 14:20  13 min" in out
    assert "mostly POST /api/checkout" in out
    # --until without an offset is UTC: 16:00Z is 17:00 in the log's +01:00
    assert "→ 2026-11-08 16:59 (+0100)" in out


def test_cli_reports_missing_files(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["nope.log"]) == 2
    assert "no such file: nope.log" in capsys.readouterr().err
