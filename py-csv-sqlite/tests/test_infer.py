"""Type inference: per-cell classification, widening, conversion and append compatibility."""

import pytest

from py_csv_sqlite.infer import Column, Kind, classify, convert, fit, infer, widen
from py_csv_sqlite.names import to_identifier, unique_identifiers


@pytest.mark.parametrize(
    ("raw", "kind"),
    [
        ("", None),
        ("   ", None),
        (" 42 ", Kind.INTEGER),
        ("-7", Kind.INTEGER),
        ("0", Kind.INTEGER),
        ("007", Kind.TEXT),  # a code with leading zeros, not the number 7
        ("1_000", Kind.TEXT),  # int() would accept it
        ("١٢٣", Kind.TEXT),  # so would int(), for Arabic-Indic digits
        ("nan", Kind.TEXT),  # and float()
        ("-3e2", Kind.REAL),
        ("12.50", Kind.REAL),
        ("YES", Kind.BOOLEAN),
        ("false", Kind.BOOLEAN),
        ("2026-02-28", Kind.DATE),
        ("2026-02-30", Kind.TEXT),  # the right shape, but not a real day
        ("20261104", Kind.INTEGER),  # date.fromisoformat() accepts this; we don't
        ("2026-11-04 09:30", Kind.DATETIME),
        ("2026-11-04T18:45:00.25+01:00", Kind.DATETIME),
        ("Ada", Kind.TEXT),
    ],
)
def test_classify(raw: str, kind: Kind | None) -> None:
    assert classify(raw) is kind


@pytest.mark.parametrize(
    ("a", "b", "wider"),
    [
        (None, Kind.INTEGER, Kind.INTEGER),
        (Kind.REAL, None, Kind.REAL),
        (Kind.INTEGER, Kind.REAL, Kind.REAL),
        (Kind.REAL, Kind.INTEGER, Kind.REAL),
        (Kind.DATE, Kind.DATETIME, Kind.DATETIME),
        (Kind.INTEGER, Kind.BOOLEAN, Kind.TEXT),
        (Kind.INTEGER, Kind.DATE, Kind.TEXT),
    ],
)
def test_widen_is_symmetric(a: Kind | None, b: Kind | None, wider: Kind) -> None:
    assert widen(a, b) is wider
    assert widen(b, a) is wider


def test_convert_normalises_typed_values_and_keeps_text_verbatim() -> None:
    assert convert(Kind.BOOLEAN, " Yes ") == 1
    assert convert(Kind.REAL, "5") == 5.0
    assert convert(Kind.DATETIME, "2026-11-04T09:30Z") == "2026-11-04 09:30:00+00:00"
    assert convert(Kind.DATETIME, "2026-11-04") == "2026-11-04 00:00:00"
    assert convert(Kind.TEXT, " 02134 ") == " 02134 "
    assert convert(Kind.INTEGER, "") is None


def _infer(header: list[str], *rows: list[str]) -> tuple[list[Column], int]:
    columns = [Column(name, h) for name, h in zip(unique_identifiers(header), header, strict=True)]
    return columns, infer(columns, rows)


def test_infer_widens_counts_empties_and_finds_the_primary_key() -> None:
    columns, count = _infer(
        ["ID", "Price", "Note"], ["1", "10", ""], ["2", "2.5", ""], ["3", "", "hi"]
    )
    id_, price, note = columns
    assert count == 3
    assert (id_.kind, id_.primary_key) == (Kind.INTEGER, True)
    assert (price.kind, price.nulls, price.decided_by) == (Kind.REAL, 1, "2.5")
    assert (note.kind, note.nulls) == (Kind.TEXT, 2)

    (dup_id,), _ = _infer(["id"], ["1"], ["2"], ["1"])
    assert (dup_id.kind, dup_id.primary_key) == (Kind.INTEGER, False)


@pytest.mark.parametrize(
    ("new", "declared", "expected"),
    [
        (Kind.INTEGER, "TEXT", Kind.TEXT),  # this file's post codes all look numeric
        (Kind.DATE, "TEXT", Kind.DATE),
        (Kind.INTEGER, "REAL", Kind.REAL),
        (Kind.BOOLEAN, "INTEGER", Kind.BOOLEAN),
        (None, "REAL", Kind.TEXT),  # all empty: every value is NULL anyway
        (Kind.REAL, "INTEGER", None),
        (Kind.TEXT, "REAL", None),
    ],
)
def test_fit_for_append(new: Kind | None, declared: str, expected: Kind | None) -> None:
    assert fit(new, declared) is expected


@pytest.mark.parametrize(
    ("header", "identifier"),
    [
        ("Unit Price ($)", "unit_price"),
        ("Discount %", "discount_pct"),
        ("Order #", "order_no"),
        ("Zażółć gęślą", "zazolc_gesla"),
        ("2nd Address", "_2nd_address"),
        ("Größe (cm)", "grosse_cm"),
    ],
)
def test_identifiers(header: str, identifier: str) -> None:
    assert to_identifier(header) == identifier
    assert unique_identifiers([header, header.upper(), ""]) == [
        identifier,
        f"{identifier}_2",
        "column_3",
    ]
