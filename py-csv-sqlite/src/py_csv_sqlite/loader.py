"""Read a CSV twice, streaming both times: once to infer the schema, once to insert the rows."""

import csv
import sqlite3
import time
from collections.abc import Iterator
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Literal

from .infer import Column, Kind, convert, fit, infer
from .names import quote, to_identifier, unique_identifiers

type IfExists = Literal["fail", "replace", "append"]


class ImportFailed(Exception):
    """A problem with the file or the target table, phrased for the user."""


@dataclass(frozen=True, slots=True)
class Plan:
    """The result of the inference pass: everything needed to create and fill the table."""

    path: Path
    table: str
    columns: list[Column]
    rows: int


@dataclass(frozen=True, slots=True)
class Loaded:
    plan: Plan
    rows: int
    seconds: float
    appended: bool


def read_rows(path: Path) -> Iterator[tuple[int, list[str]]]:
    """Yield (line number, cells) for every non-blank line, the header included."""
    with path.open(newline="", encoding="utf-8-sig") as file:
        sample = file.read(64 * 1024)
        file.seek(0)
        try:
            dialect: type[csv.Dialect] = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error:  # one column, or nothing to go on: plain commas
            dialect = csv.excel
        reader = csv.reader(file, dialect)
        for row in reader:
            if any(cell.strip() for cell in row):
                yield reader.line_num, row


def survey(path: Path, table: str | None = None) -> Plan:
    """Pass 1: name the columns, check every row's width, and infer each column's kind."""
    try:
        rows = read_rows(path)
        try:
            _, header = next(rows)
        except StopIteration:
            raise ImportFailed(f"{path}: empty file, not even a header") from None
        columns = [
            Column(name, header=h)
            for name, h in zip(unique_identifiers(header), header, strict=True)
        ]
        ragged: list[int] = []

        def well_formed() -> Iterator[list[str]]:
            for line, row in rows:
                if len(row) == len(columns):
                    yield row
                else:
                    ragged.append(line)

        count = infer(columns, well_formed())
    except (OSError, UnicodeDecodeError, csv.Error) as error:
        raise ImportFailed(f"{path}: {error}") from error
    if ragged:
        shown = ", ".join(map(str, ragged[:5])) + (" …" if len(ragged) > 5 else "")
        raise ImportFailed(
            f"{path}: {len(ragged)} row(s) don't have {len(columns)} fields (line {shown})"
        )
    return Plan(path, to_identifier(table or path.stem, fallback="data"), columns, count)


def column_sql(column: Column) -> str:
    """One column definition. STRICT enforces the storage type; CHECK enforces the rest."""
    name = quote(column.name)
    kind = column.sql_kind
    parts = [name, kind.storage]
    if column.primary_key:
        parts.append("PRIMARY KEY")
    elif column.nulls == 0:
        parts.append("NOT NULL")
    match kind:
        case Kind.BOOLEAN:
            parts.append(f"CHECK ({name} IN (0, 1))")
        case Kind.DATE:
            parts.append(f"CHECK ({name} IS date({name}))")  # NULL IS NULL, so NULLs pass
        case Kind.DATETIME:
            parts.append(f"CHECK ({name} IS NULL OR julianday({name}) IS NOT NULL)")
    return " ".join(parts)


def create_sql(plan: Plan) -> str:
    body = ",\n    ".join(column_sql(column) for column in plan.columns)
    return f"CREATE TABLE {quote(plan.table)} (\n    {body}\n) STRICT"


def _table_columns(conn: sqlite3.Connection, table: str) -> list[tuple[str, str]]:
    # pragma_table_info() is the table-valued form of PRAGMA table_info, so the
    # table name can be a bound parameter instead of being pasted into the SQL.
    rows = conn.execute("SELECT name, type FROM pragma_table_info(?)", (table,))
    return [(name, type_) for name, type_ in rows]


def _kinds_for_append(plan: Plan, existing: list[tuple[str, str]]) -> list[Kind]:
    names = [column.name for column in plan.columns]
    if names != [name for name, _ in existing]:
        raise ImportFailed(
            f"{plan.path}: columns ({', '.join(names)}) don't match table {plan.table} "
            f"({', '.join(name for name, _ in existing)})"
        )
    kinds: list[Kind] = []
    for column, (_, declared) in zip(plan.columns, existing, strict=True):
        kind = fit(column.kind, declared)
        if kind is None:
            raise ImportFailed(
                f"{plan.path}: column {column.name} looks {column.sql_kind.upper()} "
                f"but {plan.table}.{column.name} stores {declared}"
            )
        kinds.append(kind)
    return kinds


def load(conn: sqlite3.Connection, plan: Plan, if_exists: IfExists = "fail") -> Loaded:
    """Pass 2: create the table and insert every row, all in one transaction.

    `conn` must be opened with autocommit=False, so `with conn:` commits on success and rolls
    back everything, the DROP and CREATE included, on any error.
    """
    started = time.perf_counter()
    current_line = 0

    def values(kinds: list[Kind]) -> Iterator[tuple[int | float | str | None, ...]]:
        nonlocal current_line
        converters = [partial(convert, kind) for kind in kinds]
        rows = read_rows(plan.path)
        next(rows)  # the header
        for line, row in rows:
            current_line = line  # executemany pulls rows one at a time, so this is "now"
            yield tuple(conv(cell) for conv, cell in zip(converters, row, strict=True))

    with conn:
        existing = _table_columns(conn, plan.table)
        appending = bool(existing) and if_exists == "append"
        if existing and if_exists == "fail":
            raise ImportFailed(
                f"table {plan.table} already exists (use --if-exists replace or append)"
            )
        if appending:
            kinds = _kinds_for_append(plan, existing)
        else:
            conn.execute(f"DROP TABLE IF EXISTS {quote(plan.table)}")
            conn.execute(create_sql(plan))
            kinds = [column.sql_kind for column in plan.columns]
        placeholders = ", ".join("?" * len(kinds))
        try:
            cursor = conn.executemany(
                f"INSERT INTO {quote(plan.table)} VALUES ({placeholders})", values(kinds)
            )
        except sqlite3.IntegrityError as error:
            # The generator's last row is the one SQLite just refused.
            raise ImportFailed(f"{plan.path}, line {current_line}: {error}") from error
    return Loaded(plan, cursor.rowcount, time.perf_counter() - started, appending)
