"""Every unit the converter knows, and every name you might type for it.

A unit is defined by how to reach its dimension's base unit: base = value * scale + offset.
Only temperatures need an offset. Scales are Fractions, so a km/h is exactly 5/18 m/s rather
than 0.2777... rounded somewhere.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from difflib import get_close_matches
from enum import StrEnum
from fractions import Fraction


class ConversionError(ValueError):
    """Anything the user typed that can't be converted. The message is shown as-is."""


class Dimension(StrEnum):
    LENGTH = "length"
    MASS = "mass"
    VOLUME = "volume"
    TIME = "time"
    SPEED = "speed"
    DATA = "data"
    TEMPERATURE = "temperature"


@dataclass(frozen=True, slots=True)
class Unit:
    symbol: str
    dimension: Dimension
    scale: Fraction
    offset: Fraction = Fraction(0)
    # Extra spellings take part in lookup but not in equality or the repr.
    names: tuple[str, ...] = field(default=(), compare=False, repr=False)

    @property
    def name(self) -> str:
        return self.names[0] if self.names else self.symbol

    def __str__(self) -> str:
        return self.symbol


# Exact legal definitions; everything imperial is derived from these.
_INCH = Fraction("0.0254")
_FOOT = 12 * _INCH
_MILE = 5280 * _FOOT
_POUND = Fraction("0.45359237")
_GALLON = Fraction("3.785411784")  # US liquid gallon: 231 cubic inches, in litres
_FL_OZ = _GALLON / 128
_HOUR = Fraction(3600)
_ZERO_C = Fraction("273.15")

# symbol -> (scale, names). Names are comma-separated; "metre"/"litre" get US spellings for free.
_TABLE: dict[Dimension, dict[str, tuple[Fraction | int, str]]] = {
    Dimension.LENGTH: {
        "mm": (Fraction(1, 1000), "millimetre, millimetres"),
        "cm": (Fraction(1, 100), "centimetre, centimetres"),
        "m": (1, "metre, metres"),
        "km": (1000, "kilometre, kilometres"),
        "in": (_INCH, "inch, inches"),
        "ft": (_FOOT, "foot, feet"),
        "yd": (3 * _FOOT, "yard, yards"),
        "mi": (_MILE, "mile, miles"),
        "nmi": (1852, "nautical-mile, nautical-miles"),
    },
    Dimension.MASS: {
        "mg": (Fraction(1, 1_000_000), "milligram, milligrams"),
        "g": (Fraction(1, 1000), "gram, grams"),
        "kg": (1, "kilogram, kilograms, kilo, kilos"),
        "t": (1000, "tonne, tonnes"),
        "oz": (_POUND / 16, "ounce, ounces"),
        "lb": (_POUND, "pound, pounds, lbs"),
        "st": (14 * _POUND, "stone, stones"),
    },
    Dimension.VOLUME: {
        "ml": (Fraction(1, 1000), "millilitre, millilitres, mL"),
        "l": (1, "litre, litres, L"),
        "m3": (1000, "cubic-metre, cubic-metres"),
        "tsp": (_FL_OZ / 6, "teaspoon, teaspoons"),
        "tbsp": (_FL_OZ / 2, "tablespoon, tablespoons"),
        "floz": (_FL_OZ, "fluid-ounce, fluid-ounces"),
        "cup": (8 * _FL_OZ, "cup, cups"),
        "pt": (16 * _FL_OZ, "pint, pints"),
        "qt": (32 * _FL_OZ, "quart, quarts"),
        "gal": (_GALLON, "gallon, gallons"),
    },
    Dimension.TIME: {
        "ms": (Fraction(1, 1000), "millisecond, milliseconds"),
        "s": (1, "second, seconds, sec"),
        "min": (60, "minute, minutes"),
        "h": (_HOUR, "hour, hours, hr"),
        "d": (24 * _HOUR, "day, days"),
        "wk": (7 * 24 * _HOUR, "week, weeks"),
        "yr": (Fraction("365.25") * 24 * _HOUR, "year, years"),  # Julian year
    },
    Dimension.SPEED: {
        "m/s": (1, "metres-per-second, mps"),
        "km/h": (1000 / _HOUR, "kilometres-per-hour, kph, kmh"),
        "mph": (_MILE / _HOUR, "miles-per-hour"),
        "kn": (1852 / _HOUR, "knot, knots"),
    },
    Dimension.DATA: {
        "bit": (Fraction(1, 8), "bit, bits"),
        "B": (1, "byte, bytes"),
        "kB": (10**3, "kilobyte, kilobytes"),
        "MB": (10**6, "megabyte, megabytes"),
        "GB": (10**9, "gigabyte, gigabytes"),
        "TB": (10**12, "terabyte, terabytes"),
        "KiB": (2**10, "kibibyte, kibibytes"),
        "MiB": (2**20, "mebibyte, mebibytes"),
        "GiB": (2**30, "gibibyte, gibibytes"),
        "TiB": (2**40, "tebibyte, tebibytes"),
    },
}

_TEMPERATURES = (
    Unit("K", Dimension.TEMPERATURE, Fraction(1), names=("kelvin",)),
    Unit("°C", Dimension.TEMPERATURE, Fraction(1), _ZERO_C, ("celsius", "C", "degC")),
    # K = (F + 459.67) * 5/9, so the offset is 459.67 * 5/9.
    Unit("°F", Dimension.TEMPERATURE, Fraction(5, 9), Fraction("459.67") * 5 / 9,
         ("fahrenheit", "F", "degF")),
)  # fmt: skip

UNITS: tuple[Unit, ...] = (
    *(
        Unit(symbol, dimension, Fraction(scale), names=tuple(n.strip() for n in names.split(",")))
        for dimension, rows in _TABLE.items()
        for symbol, (scale, names) in rows.items()
    ),
    *_TEMPERATURES,
)

BASE_UNIT: dict[Dimension, Unit] = {u.dimension: u for u in UNITS if u.scale == 1 and not u.offset}


def spellings(unit: Unit) -> set[str]:
    """Every string that names this unit: symbol, names, and US spellings of -metre/-litre."""
    found = {unit.symbol, *unit.names}
    return found | {s.replace("metre", "meter").replace("litre", "liter") for s in found}


# A dict instead of a 70-arm switch: lookup is data, so adding a unit is one table row.
_BY_NAME: dict[str, Unit] = {spelling: u for u in UNITS for spelling in spellings(u)}
_BY_FOLDED: defaultdict[str, set[Unit]] = defaultdict(set)
for _unit in UNITS:
    for _spelling in spellings(_unit):
        _BY_FOLDED[_spelling.casefold()].add(_unit)


def lookup(name: str) -> Unit:
    """Find a unit by exact name, then case-insensitively if that is unambiguous."""
    if unit := _BY_NAME.get(name):
        return unit
    match sorted(_BY_FOLDED.get(name.casefold(), ()), key=str):
        case [unit]:
            return unit
        case []:
            close = get_close_matches(name, _BY_NAME, n=3, cutoff=0.7)
            hint = (
                f". Did you mean {', '.join(close)}?" if close else ". Type 'units' to list them."
            )
            raise ConversionError(f"unknown unit {name!r}{hint}")
        case candidates:
            options = " or ".join(u.symbol for u in candidates)
            raise ConversionError(f"{name!r} is ambiguous: {options}")


def dimension_named(name: str) -> Dimension:
    try:
        return Dimension(name.casefold())
    except ValueError:
        known = ", ".join(Dimension)
        raise ConversionError(f"no dimension called {name!r}; try one of {known}") from None
