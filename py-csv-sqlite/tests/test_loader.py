"""End to end against real SQLite: schema, enforcement, transactions, queries and the CLI."""

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from py_csv_sqlite import main
from py_csv_sqlite.db import connect, run
from py_csv_sqlite.loader import ImportFailed, load, survey

PEOPLE = """\
ID;Name;Born;Active;Post Code
1;Ada Lovelace;1815-12-10;yes;02134
2;Grace Hopper;1906-12-09;no;10001
3;Edsger Dijkstra;;yes;01067
"""


@pytest.fixture
def people(tmp_path: Path) -> Path:
    path = tmp_path / "People List.csv"
    # A BOM and semicolons, the way Excel saves "CSV" in much of Europe.
    path.write_text(PEOPLE, encoding="utf-8-sig", newline="")
    return path


@pytest.fixture
def conn() -> Iterator[sqlite3.Connection]:
    conn = connect(":memory:")
    yield conn
    conn.close()


def test_import_stores_real_types(people: Path, conn: sqlite3.Connection) -> None:
    loaded = load(conn, survey(people))
    assert (loaded.plan.table, loaded.rows) == ("people_list", 3)
    row = conn.execute(
        "SELECT typeof(id), typeof(born), active, post_code FROM people_list WHERE name = ?",
        ("Ada Lovelace",),
    ).fetchone()
    assert row == ("integer", "text", 1, "02134")
    assert conn.execute("SELECT born FROM people_list WHERE id = 3").fetchone() == (None,)


def test_strict_and_check_constraints_guard_the_table(
    people: Path, conn: sqlite3.Connection
) -> None:
    load(conn, survey(people))
    for bad in (
        "INSERT INTO people_list VALUES (4, 'X', '1999-02-30', 1, '1')",  # not a date
        "INSERT INTO people_list VALUES (4, 'X', NULL, 2, '1')",  # not a boolean
        "INSERT INTO people_list VALUES ('four', 'X', NULL, 1, '1')",  # STRICT: not an integer
        "INSERT INTO people_list VALUES (1, 'X', NULL, 1, '1')",  # duplicate primary key
    ):
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(bad)
        conn.rollback()


def test_failed_append_rolls_back_and_names_the_line(
    people: Path, conn: sqlite3.Connection, tmp_path: Path
) -> None:
    load(conn, survey(people))
    with pytest.raises(ImportFailed, match="already exists"):
        load(conn, survey(people))  # the default is if_exists="fail"
    more = tmp_path / "more.csv"
    more.write_text("ID,Name,Born,Active,Post Code\n4,Linus,,no,00100\n2,Dup,,no,1\n")
    with pytest.raises(ImportFailed, match=r"line 3: UNIQUE constraint failed: people_list\.id"):
        load(conn, survey(more, table="people list"), if_exists="append")
    # Linus (line 2) went in before the failure, and the rollback took him out again.
    assert conn.execute("SELECT count(*) FROM people_list").fetchone() == (3,)


def test_ragged_rows_are_reported_before_anything_is_written(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("a,b\n1,2\n3\n\n4,5,6\n")
    with pytest.raises(ImportFailed, match=r"2 row\(s\) don't have 2 fields \(line 3, 5\)"):
        survey(path)


def test_regexp_and_queries(people: Path, conn: sqlite3.Connection) -> None:
    load(conn, survey(people))
    result = run(conn, "SELECT name FROM people_list WHERE name REGEXP '^[AE]' ORDER BY id")
    assert result.columns == ["name"]
    assert result.rows == [("Ada Lovelace",), ("Edsger Dijkstra",)]
    assert run(conn, "UPDATE people_list SET active = 0").changed == 3


def test_cli_queries_csv_files_in_memory(people: Path, capsys: pytest.CaptureFixture[str]) -> None:
    sql = "SELECT count(*) AS active FROM people_list WHERE active"
    assert main([str(people), "-q", sql]) == 0
    out, err = capsys.readouterr()
    assert out.splitlines() == ["active", "------", "     2", "(1 row)"]
    assert "people_list  (3 rows" in err

    assert main([str(people), "-q", "SELECT nope FROM people_list"]) == 1
    assert "csv2db: query 1: no such column: nope" in capsys.readouterr().err
