"""`csv2db`: load CSV files into SQLite with inferred, enforced column types, then query them.

csv2db data/orders.csv data/customers.csv -q "SELECT ..."      (SQL over CSVs, in memory)
csv2db data/*.csv -o shop.db                                    (build a database file)
csv2db data/messy.tsv --dry-run                                 (just show the schema)
"""

import argparse
import sqlite3
import sys
from collections.abc import Sequence
from contextlib import closing
from pathlib import Path

from . import render
from .db import connect, run
from .loader import ImportFailed, Plan, create_sql, load, survey


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="csv2db",
        description=__doc__.splitlines()[0].removeprefix("`csv2db`: "),
        epilog="Summaries and schemas go to stderr, query results to stdout.",
    )
    parser.add_argument("files", nargs="+", type=Path, metavar="FILE", help="CSV/TSV files")
    parser.add_argument(
        "-o", "--db", default=":memory:", help="database file (default: in memory, gone on exit)"
    )
    parser.add_argument("-t", "--table", help="table name (default: the file name; one file only)")
    parser.add_argument(
        "--if-exists",
        choices=["fail", "replace", "append"],
        default="fail",
        help="when the table is already there (default: fail)",
    )
    parser.add_argument(
        "-q",
        "--sql",
        action="append",
        default=[],
        metavar="SQL",
        help="run a query after importing; repeat for more (REGEXP works too)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="print the CREATE TABLE statements, import nothing"
    )
    return parser


def _import(args: argparse.Namespace, plans: Sequence[Plan]) -> None:
    label = "memory" if args.db == ":memory:" else args.db
    # closing(): `with conn:` only ends the transaction, the connection stays open.
    with closing(connect(args.db)) as conn:
        for plan in plans:
            loaded = load(conn, plan, args.if_exists)
            print(render.summary(loaded, label), file=sys.stderr)
            if not args.sql and not loaded.appended:
                print(render.schema(plan), end="\n\n", file=sys.stderr)
        for n, sql in enumerate(args.sql, start=1):
            try:
                print(render.result(run(conn, sql)))
            except sqlite3.Error as error:
                raise ImportFailed(f"query {n}: {error}") from error
            if n < len(args.sql):
                print()
    if args.db != ":memory:" and not args.sql:
        print(f"Open it with: uv run python -m sqlite3 {args.db}", file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.table and len(args.files) > 1:
        parser.error("--table only works with a single file")
    try:
        plans = [survey(path, args.table) for path in args.files]
        if args.dry_run:
            for plan in plans:
                print(f"{plan.path}: {plan.rows:,} rows\n{render.schema(plan)}\n")
                print(create_sql(plan) + ";\n")
            return 0
        _import(args, plans)
    except ImportFailed as error:
        print(f"csv2db: {error}", file=sys.stderr)
        return 1
    except sqlite3.Error as error:
        print(f"csv2db: {args.db}: {error}", file=sys.stderr)
        return 1
    return 0
