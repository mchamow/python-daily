"""The JSON codec and due-date parsing: pure functions, no files."""

import json
from datetime import UTC, date, datetime

import pytest

from py_todo_cli.codec import DecodeError, dumps, loads
from py_todo_cli.dates import describe_due, parse_due
from py_todo_cli.model import Priority, Task, TodoFile

SUNDAY = date(2026, 10, 25)


@pytest.fixture
def todo() -> TodoFile:
    now = datetime(2026, 10, 25, 9, 30, tzinfo=UTC)
    todo = TodoFile()
    todo.add("Renew passport", now=now, priority=Priority.HIGH, tags=["admin"], due=SUNDAY)
    todo.add("Read PEP 695", now=now, priority=Priority.LOW)
    todo.tasks[1].done = now
    return todo


def test_round_trip_keeps_every_type(todo: TodoFile) -> None:
    text = dumps(todo)
    raw = json.loads(text)
    assert raw["tasks"][0]["priority"] == "high"  # StrEnum is a str: no encoder needed
    assert raw["tasks"][0]["due"] == "2026-10-25"
    assert raw["tasks"][1]["done"] == "2026-10-25T09:30:00+00:00"

    back = loads(TodoFile, text)
    assert back == todo  # dataclasses compare field by field
    assert isinstance(back.tasks[0].priority, Priority)
    assert isinstance(back.tasks[0].created, datetime)
    assert type(back.tasks[0].due) is date


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"priority": "urgent"}, r"\$\.tasks\[0\]\.priority: expected one of low, normal, high"),
        ({"due": "friday"}, r"\$\.tasks\[0\]\.due: expected date, got 'friday'"),
        ({"id": True}, r"\$\.tasks\[0\]\.id: expected int, got True"),  # bool is not an int here
        ({"tags": "home"}, r"\$\.tasks\[0\]\.tags: expected a list"),
        ({"colour": "red"}, r"\$\.tasks\[0\]: unknown field\(s\) colour"),
    ],
)
def test_decode_errors_name_the_path(
    todo: TodoFile, change: dict[str, object], message: str
) -> None:
    raw = json.loads(dumps(todo))
    raw["tasks"][0] |= change
    with pytest.raises(DecodeError, match=message):
        loads(TodoFile, json.dumps(raw))


def test_decode_reports_missing_required_fields() -> None:
    with pytest.raises(DecodeError, match=r"\$\.tasks\[0\]\.title: missing"):
        loads(TodoFile, '{"tasks": [{"id": 1, "created": "2026-10-25T09:00:00"}]}')


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("today", SUNDAY),
        ("Tomorrow", date(2026, 10, 26)),
        ("fri", date(2026, 10, 30)),
        ("sunday", date(2026, 11, 1)),  # strictly after today, so a week ahead
        ("+3d", date(2026, 10, 28)),
        ("+2w", date(2026, 11, 8)),
        ("2026-12-24", date(2026, 12, 24)),
    ],
)
def test_parse_due(text: str, expected: date) -> None:
    assert parse_due(text, SUNDAY) == expected


def test_bad_due_dates_and_descriptions() -> None:
    for text in ("someday", "fr", "+3m", "2026-13-01"):
        with pytest.raises(ValueError, match="can't read due date"):
            parse_due(text, SUNDAY)
    assert [describe_due(date(2026, 10, d), SUNDAY) for d in (22, 25, 26, 29)] == [
        "overdue 3d",
        "today",
        "tomorrow",
        "thu",
    ]
    assert describe_due(date(2026, 11, 20), SUNDAY) == "2026-11-20"


def test_tasks_never_share_a_default_list() -> None:
    now = datetime.now(UTC)
    a, b = Task(1, "a", now), Task(2, "b", now)
    a.tags.append("x")
    assert b.tags == []
