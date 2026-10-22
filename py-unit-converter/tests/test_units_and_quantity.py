"""The unit table, exact conversions, and Decimal rendering."""

from fractions import Fraction

import pytest

from py_unit_converter.quantity import Quantity, describe, render, total
from py_unit_converter.units import UNITS, ConversionError, lookup, spellings


def q(value: str, unit: str) -> Quantity:
    return Quantity(Fraction(value), lookup(unit))


def test_every_spelling_finds_its_own_unit() -> None:
    # Catches two units claiming the same name: the dict would silently keep only the last.
    for unit in UNITS:
        for spelling in spellings(unit):
            assert lookup(spelling) is unit, spelling


@pytest.mark.parametrize(
    ("typed", "symbol"),
    [("KM", "km"), ("Kilometers", "km"), ("mb", "MB"), ("c", "°C"), ("liters", "l")],
)
def test_lookup_falls_back_to_case_insensitive(typed: str, symbol: str) -> None:
    assert lookup(typed).symbol == symbol


def test_unknown_unit_suggests_close_spellings() -> None:
    with pytest.raises(ConversionError, match="Did you mean kilometer"):
        lookup("kilomter")


def test_imperial_units_match_their_legal_definitions() -> None:
    assert lookup("mi").scale == Fraction("1609.344")  # metres, exactly
    inch_in_dm = lookup("in").scale * 10  # a litre is a cubic decimetre
    assert lookup("gal").scale == 231 * inch_in_dm**3  # the US gallon is 231 cubic inches


@pytest.mark.parametrize(
    ("source", "target", "expected"),
    [
        (q("1", "mi"), "km", Fraction("1.609344")),
        (q("98.6", "F"), "C", Fraction(37)),
        (q("-40", "C"), "F", Fraction(-40)),
        (q("0", "K"), "C", Fraction("-273.15")),
        (q("1", "km/h"), "m/s", Fraction(5, 18)),
        (q("1", "GiB"), "MB", Fraction("1073.741824")),
    ],
    ids=["mile", "body-temp", "crossover", "absolute-zero", "speed", "binary-prefix"],
)
def test_conversions_are_exact(source: Quantity, target: str, expected: Fraction) -> None:
    assert source.to(lookup(target)).value == expected


def test_converting_across_dimensions_fails() -> None:
    with pytest.raises(ConversionError, match=r"can't convert kg \(mass\) to m \(length\)"):
        q("1", "kg").to(lookup("m"))


def test_total_adds_parts_in_the_first_unit() -> None:
    assert total([q("5", "ft"), q("11", "in")]) == Quantity(Fraction(71, 12), lookup("ft"))


def test_total_refuses_to_add_offset_temperatures() -> None:
    with pytest.raises(ConversionError, match="use K"):
        total([q("5", "C"), q("5", "C")])


@pytest.mark.parametrize(
    ("value", "digits", "text", "exact"),
    [
        (Fraction(1, 4), 10, "0.25", True),
        (Fraction(5, 18), 10, "0.2777777778", False),
        (Fraction(1609344), 10, "1,609,344", True),
        (Fraction(1609344), 3, "1,610,000", False),  # rounding an integer is inexact too
        (Fraction(8 * 10**12), 10, "8e+12", True),
        (Fraction(1, 10**9), 10, "1e-9", True),
    ],
)
def test_render_reports_whether_rounding_happened(
    value: Fraction, digits: int, text: str, exact: bool
) -> None:
    shown = render(value, digits)
    assert (shown.text, shown.exact) == (text, exact)


def test_describe_adds_the_exact_fraction_when_it_is_short() -> None:
    assert describe(q("1", "km/h").to(lookup("m/s")), 4) == "≈ 0.2778 m/s  (exactly 5/18)"
