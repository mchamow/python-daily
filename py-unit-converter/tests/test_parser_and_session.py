"""Parsing lines into commands, the REPL session, and the command-line entry point."""

import io
from fractions import Fraction

import pytest

from py_unit_converter import main, run_lines
from py_unit_converter.parser import (
    Blank,
    Command,
    Convert,
    ConvertToAll,
    ListDimensions,
    ListUnits,
    Quit,
    SetDigits,
    parse,
)
from py_unit_converter.quantity import Quantity
from py_unit_converter.session import Session
from py_unit_converter.units import ConversionError, Dimension, lookup


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("", Blank()),
        ("quit", Quit()),
        ("units", ListDimensions()),
        ("units MASS", ListUnits(Dimension.MASS)),
        ("digits 20", SetDigits(20)),
        ("10km to mi", Convert(Quantity(Fraction(10), lookup("km")), lookup("mi"), "10 km")),
        (
            "1/2 cup -> ml",
            Convert(Quantity(Fraction(1, 2), lookup("cup")), lookup("ml"), "1/2 cup"),
        ),
        ("mi", ConvertToAll(Quantity(Fraction(1), lookup("mi")), "mi")),
    ],
)
def test_parse_recognises_each_shape(line: str, expected: Command) -> None:
    assert parse(line) == expected


@pytest.mark.parametrize(
    ("line", "message"),
    [
        ("digits 0", "whole number from 1"),
        ("10 km to", "to what"),
        ("5 ft 11 to cm", "number-unit pairs"),
        ("ans to ft", "no previous answer"),
        ("ten km to mi", "not a number"),
        ("1 parsec to km", "unknown unit"),
    ],
)
def test_parse_errors_explain_themselves(line: str, message: str) -> None:
    with pytest.raises(ConversionError, match=message):
        parse(line)


def test_session_remembers_answer_and_precision() -> None:
    session = Session()
    assert session.execute("1 tsp to ml") == "1 tsp ≈ 4.928921594 ml"
    assert session.execute("digits 20") == "showing 20 significant digits"
    assert session.execute("ans to ml") == "ans = 4.92892159375 ml"  # the exact value was kept
    assert session.execute("_ to tsp") == "_ = 1 tsp"
    assert session.execute("quit") is None


def test_batch_mode_reports_bad_lines_and_carries_on() -> None:
    out, err = io.StringIO(), io.StringIO()
    status = run_lines(
        Session(), ["1 mi to km", "1 kg to m", "", "1 ft to in", "quit", "1 m"], out, err
    )
    assert status == 1
    assert out.getvalue() == "1 mi = 1.609344 km\n1 ft = 12 in\n"  # nothing after quit
    assert err.getvalue() == "conv: line 2: can't convert kg (mass) to m (length)\n"


def test_main_one_shot(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--digits", "4", "100", "km/h", "to", "mph"]) == 0
    assert capsys.readouterr().out == "100 km/h ≈ 62.14 mph\n"
