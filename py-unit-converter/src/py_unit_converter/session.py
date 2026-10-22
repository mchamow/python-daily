"""A REPL session: remembers the last answer and the display precision between lines."""

from dataclasses import dataclass
from fractions import Fraction
from typing import assert_never

from .parser import (
    Blank,
    Convert,
    ConvertToAll,
    Help,
    ListDimensions,
    ListUnits,
    Quit,
    SetDigits,
    parse,
)
from .quantity import Quantity, describe
from .units import BASE_UNIT, UNITS, Dimension, Unit

HELP = """\
  10 km to mi          convert (also: as, ->)
  5 ft 11 in to cm     add up parts first
  1 mi                 show it in every unit of its dimension
  ans to ft            reuse the previous answer (or _)
  units [dimension]    list units, or one dimension's definitions
  digits 20            significant digits to show (default 10)
  quit                 or Ctrl-D

  '=' means every digit shown is exact; '≈' means the value was rounded to fit."""


@dataclass
class Session:
    digits: int = 10
    ans: Quantity | None = None

    def execute(self, line: str) -> str | None:
        """Run one line and return what to print, or None if the user asked to quit.

        Raises ConversionError for bad input; the caller decides how to show it.
        """
        # Class patterns: `Convert(quantity, target, label)` checks the type, then binds the
        # fields positionally, in the order the dataclass declares them.
        match command := parse(line, ans=self.ans):
            case Blank():
                return ""
            case Quit():
                return None
            case Help():
                return HELP
            case SetDigits(digits):
                self.digits = digits
                return f"showing {digits} significant digits"
            case ListDimensions():
                return _overview()
            case ListUnits(dimension):
                return self._definitions(dimension)
            case ConvertToAll(quantity, label):
                self.ans = quantity
                return self._every_unit(quantity, label)
            case Convert(quantity, target, label):
                self.ans = quantity.to(target)
                return f"{label} {describe(self.ans, self.digits)}"
            case _:
                # mypy proves this unreachable; add a Command without a case and it won't be.
                assert_never(command)

    def _every_unit(self, quantity: Quantity, label: str) -> str:
        others = [u for u in UNITS if u.dimension is quantity.unit.dimension and u != quantity.unit]
        lines = [describe(quantity.to(unit), self.digits) for unit in others]
        return "\n".join([label, *(f"  {line}" for line in lines)])

    def _definitions(self, dimension: Dimension) -> str:
        base = BASE_UNIT[dimension]
        rows = []
        for unit in (u for u in UNITS if u.dimension is dimension):
            match unit.scale, unit.offset:
                case 1, 0:
                    definition = "base unit"
                case _, 0:
                    definition = (
                        f"1 {unit} {describe(Quantity(Fraction(1), unit).to(base), self.digits)}"
                    )
                case _:  # offset scales are best described by where their zero sits
                    definition = (
                        f"0 {unit} {describe(Quantity(Fraction(0), unit).to(base), self.digits)}"
                    )
            rows.append(f"  {unit.symbol:<5} {unit.name:<20} {definition}")
        return "\n".join([f"{dimension} (base unit: {base})", *rows])


def _overview() -> str:
    by_dimension: dict[Dimension, list[Unit]] = {}
    for unit in UNITS:
        by_dimension.setdefault(unit.dimension, []).append(unit)
    width = max(map(len, Dimension))
    return "\n".join(
        f"  {dimension:<{width}}  {' '.join(map(str, units))}"
        for dimension, units in by_dimension.items()
    )
