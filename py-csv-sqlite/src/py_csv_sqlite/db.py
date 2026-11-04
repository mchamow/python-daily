"""The SQLite side: opening a connection, a Python REGEXP, and running ad-hoc queries."""

import re
import sqlite3
from dataclasses import dataclass

type Value = int | float | str | bytes | None


def _regexp(pattern: str, value: Value) -> bool:
    # SQLite rewrites `X REGEXP Y` as regexp(Y, X): the pattern comes first.
    # re caches compiled patterns, so this doesn't recompile once per row.
    return value is not None and re.search(pattern, str(value)) is not None


def connect(target: str) -> sqlite3.Connection:
    """Open a database file (or ':memory:') the PEP 249 way, plus a REGEXP operator.

    autocommit=False (Python 3.12+) means a transaction is always open: nothing is saved until
    commit(), and `with conn:` commits or rolls back. It does *not* close the connection.
    """
    conn = sqlite3.connect(target, autocommit=False)
    conn.create_function("regexp", 2, _regexp, deterministic=True)
    return conn


@dataclass(frozen=True, slots=True)
class Result:
    columns: list[str]  # empty for statements that return no rows (INSERT, UPDATE, ...)
    rows: list[tuple[Value, ...]]
    changed: int = 0


def run(conn: sqlite3.Connection, sql: str) -> Result:
    """Run one statement in its own transaction and fetch everything it returns."""
    with conn:
        cursor = conn.execute(sql)
        if cursor.description is None:
            return Result([], [], changed=cursor.rowcount)
        # description is a 7-tuple per column (DB-API); only the name is filled in by sqlite3.
        columns = [entry[0] for entry in cursor.description]
        return Result(columns, cursor.fetchall())
