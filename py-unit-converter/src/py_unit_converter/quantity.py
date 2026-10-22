"""Quantities: exact arithmetic with Fraction, shown to the user through Decimal.

Fraction keeps every conversion exact (5/18 stays 5/18). Decimal turns the result into digits at
a chosen precision, and its context *tells us* whether that rounding lost anything.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal, Inexact, localcontext
from fractions import Fraction

from .units import ConversionError, Unit


@dataclass(frozen=True, slots=True)
class Quantity:
    value: Fraction
    unit: Unit

    # Python 3.14 evaluates annotations lazily, so a method can return its own class unquoted.
    def to(self, target: Unit) -> Quantity:
        if target.dimension is not self.unit.dimension:
            have, want = self.unit, target
            raise ConversionError(
                f"can't convert {have} ({have.dimension}) to {want} ({want.dimension})"
            )
        base = self.value * self.unit.scale + self.unit.offset
        return Quantity((base - target.offset) / target.scale, target)


def total(parts: Sequence[Quantity]) -> Quantity:
    """Add up `5 ft 11 in`-style parts, expressed in the first part's unit."""
    if not parts:
        raise ConversionError("nothing to convert")
    first, *rest = parts
    if rest and any(part.unit.offset for part in parts):
        # 5 °C + 5 °C is not 10 °C once you go through kelvin, so refuse rather than guess.
        raise ConversionError(f"can't add up {first.unit.dimension}s on °C/°F scales; use K")
    extra = sum((part.to(first.unit).value for part in rest), start=Fraction(0))
    return Quantity(first.value + extra, first.unit)


@dataclass(frozen=True, slots=True)
class Rendered:
    text: str
    exact: bool  # False when the digits shown are a rounding of the true value


def render(value: Fraction, digits: int) -> Rendered:
    """Format to `digits` significant digits, and report whether that was lossless."""
    with localcontext(prec=digits) as ctx:
        ctx.clear_flags()
        number = (Decimal(value.numerator) / Decimal(value.denominator)).normalize()
        exact = not ctx.flags[Inexact]  # set by the division if it had to round
    match number.adjusted():  # the power of ten of the leading digit
        case power if power >= 12 or power < -6:
            text = f"{number:e}"
        case _:
            text = f"{number:,f}"
    return Rendered(text, exact)


def describe(quantity: Quantity, digits: int) -> str:
    """`≈ 0.2777777778 m/s (exactly 5/18)`: the sign says whether you can trust every digit."""
    shown = render(quantity.value, digits)
    text = f"{'=' if shown.exact else '≈'} {shown.text} {quantity.unit}"
    if not shown.exact and quantity.value.denominator <= 1000:
        text += f"  (exactly {quantity.value})"
    return text
