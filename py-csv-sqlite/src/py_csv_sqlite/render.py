"""Plain-text output: the inferred schema and query results as aligned tables."""

from collections.abc import Sequence

from .db import Result, Value
from .loader import Loaded, Plan


def _cell(value: Value) -> str:
    match value:
        case None:
            return "NULL"
        case float() if value.is_integer() and abs(value) < 1e15:
            return f"{value:.1f}"
        case bytes():
            return f"<{len(value)} bytes>"
        case _:
            return str(value)


def table(headers: Sequence[str], rows: Sequence[Sequence[str]], right: set[int]) -> str:
    """Columns padded to their widest cell; indexes in `right` are right-aligned."""
    widths = [max(len(cell) for cell in col) for col in zip(headers, *rows, strict=True)]

    def line(cells: Sequence[str]) -> str:
        padded = (
            cell.rjust(width) if i in right else cell.ljust(width)
            for i, (cell, width) in enumerate(zip(cells, widths, strict=True))
        )
        return "  ".join(padded).rstrip()

    return "\n".join([line(headers), line(["-" * w for w in widths]), *map(line, rows)])


def result(res: Result) -> str:
    if not res.columns:
        return f"({res.changed} row(s) changed)"
    cells = [[_cell(v) for v in row] for row in res.rows]
    # A column is numeric (so right-aligned) when every non-NULL value in it is a number.
    right = {
        i
        for i in range(len(res.columns))
        if all(isinstance(row[i], int | float) for row in res.rows if row[i] is not None)
    }
    count = len(res.rows)
    return f"{table(res.columns, cells, right)}\n({count} row{'' if count == 1 else 's'})"


def schema(plan: Plan) -> str:
    """One line per column: name, inferred type, constraints, and the value that decided it."""
    rows = []
    for column in plan.columns:
        kind = column.sql_kind.upper()
        if column.primary_key:
            note = "primary key"
        elif column.nulls:
            note = f"{column.nulls} empty"
        else:
            note = "not null"
        decided_by = repr(column.decided_by) if column.decided_by else ""
        rows.append([column.name, kind, note, column.header, decided_by])
    return table(["column", "type", "", "header", "decided by"], rows, right=set())


def summary(loaded: Loaded, target: str) -> str:
    plan = loaded.plan
    verb = "appended to" if loaded.appended else "→"
    ms = loaded.seconds * 1000
    return f"{plan.path} {verb} {target}:{plan.table}  ({loaded.rows:,} rows, {ms:,.0f} ms)"
