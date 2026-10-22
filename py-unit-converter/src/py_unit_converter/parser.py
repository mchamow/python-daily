"""Turning a line of input into a command, with structural pattern matching."""

import re
from dataclasses import dataclass
from fractions import Fraction
from itertools import batched

from .quantity import Quantity, total
from .units import ConversionError, Dimension, Unit, dimension_named, lookup

MAX_DIGITS = 50


# One small frozen dataclass per command. Dataclasses generate __match_args__, so the session can
# destructure them positionally: `case Convert(quantity, target):`.
@dataclass(frozen=True, slots=True)
class Convert:
    quantity: Quantity
    target: Unit
    label: str  # what the user typed, echoed back in the answer


@dataclass(frozen=True, slots=True)
class ConvertToAll:  # "1 mi" with no target: show it in every unit of its dimension
    quantity: Quantity
    label: str


@dataclass(frozen=True, slots=True)
class ListUnits:
    dimension: Dimension


@dataclass(frozen=True, slots=True)
class ListDimensions:
    pass


@dataclass(frozen=True, slots=True)
class SetDigits:
    digits: int


@dataclass(frozen=True, slots=True)
class Help:
    pass


@dataclass(frozen=True, slots=True)
class Quit:
    pass


@dataclass(frozen=True, slots=True)
class Blank:
    pass


type Command = Convert | ConvertToAll | ListUnits | ListDimensions | SetDigits | Help | Quit | Blank

# "10km" is two tokens. The number part accepts what Fraction accepts: 1.5, 1e3, 3/4, 1_000.
_GLUED = re.compile(
    r"(?P<number>[+-]?[\d_.]+(?:[eE][+-]?\d+)?(?:/\d+)?)(?P<unit>(?:[^\W\d_]|°)\S*)"
)


def tokenize(line: str) -> list[str]:
    tokens = []
    for word in line.split():
        if m := _GLUED.fullmatch(word):
            tokens += [m["number"], m["unit"]]
        else:
            tokens.append(word)
    return tokens


def parse(line: str, *, ans: Quantity | None = None) -> Command:
    """Parse one line. `ans` is the previous answer, which `ans to ft` refers to."""
    # Each case is a shape of the token list. Literals match by value, names capture,
    # `*source` captures "everything before", and `|` offers alternatives inside a pattern.
    match tokenize(line):
        case []:
            return Blank()
        case ["quit" | "exit" | "q"]:
            return Quit()
        case ["help" | "?"]:
            return Help()
        case ["units"]:
            return ListDimensions()
        case ["units", name]:
            return ListUnits(dimension_named(name))
        case ["digits", n] if n.isdecimal() and 1 <= int(n) <= MAX_DIGITS:
            return SetDigits(int(n))
        case ["digits", *_]:
            raise ConversionError(f"digits takes a whole number from 1 to {MAX_DIGITS}")
        case [*source, "to" | "as" | "->", target]:
            return Convert(_quantity(source, ans), lookup(target), " ".join(source))
        case [*source, "to" | "as" | "->"]:
            raise ConversionError(f"convert {' '.join(source) or 'what'} to what?")
        case source:
            return ConvertToAll(_quantity(source, ans), " ".join(source))


def _quantity(tokens: list[str], ans: Quantity | None) -> Quantity:
    match tokens:
        case []:
            raise ConversionError("nothing to convert")
        case ["ans" | "_"]:
            if ans is None:
                raise ConversionError("there is no previous answer yet")
            return ans
        case [unit]:  # "km to mi" means one km
            return Quantity(Fraction(1), lookup(unit))
    try:
        # batched(..., strict=True) pairs [5, ft, 11, in] up and raises if one is left over.
        pairs = list(batched(tokens, 2, strict=True))
    except ValueError:
        raise ConversionError(
            f"expected number-unit pairs like '5 ft 11 in', got {tokens}"
        ) from None
    return total([Quantity(_number(number), lookup(unit)) for number, unit in pairs])


def _number(text: str) -> Fraction:
    try:
        return Fraction(text)  # exact: Fraction("0.1") is 1/10, unlike float("0.1")
    except ValueError, ZeroDivisionError:  # PEP 758: no parentheses needed in 3.14
        raise ConversionError(f"{text!r} is not a number") from None
