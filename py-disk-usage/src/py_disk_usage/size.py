"""A byte count that knows how to print itself: ``f"{size:>9.1h}"`` -> ``"  1.5 MiB"``.

``Size`` is an ``int`` with a custom ``__format__``. Two extra presentation types are added to
the format-spec mini-language: ``h`` (binary, 1024: KiB, MiB, ... like ``du -h``) and ``H``
(decimal, 1000: kB, MB, ... like macOS Finder). Every other spec goes to ``int``, so
``f"{size:,}"`` still prints ``1,572,864``.
"""

import re
from typing import Self

BINARY = ("KiB", "MiB", "GiB", "TiB", "PiB", "EiB")
DECIMAL = ("kB", "MB", "GB", "TB", "PB", "EB")

# [[fill]align][width][.precision](h|H). Sign, "#", "0" and grouping make no sense for "1.5 MiB".
HUMAN_SPEC = re.compile(
    r"""
    (?P<align> (?: .? [<>^] )? )
    (?P<width> \d* )
    (?: \. (?P<precision> \d+ ) )?
    (?P<kind> [hH] )
    """,
    re.VERBOSE,
)


class Size(int):
    """Bytes. Behaves exactly like ``int``, except in an f-string with ``h`` or ``H``."""

    __slots__ = ()

    def __format__(self, spec: str) -> str:
        m = HUMAN_SPEC.fullmatch(spec)
        if m is None:
            return super().__format__(spec)  # ",", "_", ">12", "x", "" ... all int's business
        precision = int(m["precision"] or 1)
        base, units = (1024, BINARY) if m["kind"] == "h" else (1000, DECIMAL)
        text = human(self, base, units, precision)
        # Strings default to left-aligned; a column of sizes should line up on the right.
        return format(text, f"{m['align'] or '>'}{m['width']}")

    def __repr__(self) -> str:
        return f"Size({int(self)})"

    # int has no __str__ of its own: it inherits object.__str__, which calls repr(). Without
    # this line, str(Size(0)) and f"{Size(0)}" would both say "Size(0)".
    __str__ = int.__repr__

    # int's operators return plain int, which would forget __format__ after the first `+`.
    def __add__(self, other: int) -> Self:
        return type(self)(int(self) + other)

    def __radd__(self, other: int) -> Self:  # makes sum(sizes) a Size: 0 + Size(...) lands here
        return type(self)(other + int(self))

    def __sub__(self, other: int) -> Self:
        return type(self)(int(self) - other)


def human(n: int, base: int, units: tuple[str, ...], precision: int) -> str:
    """``1536`` -> ``"1.5 KiB"``. Bytes are always whole, so they never get decimals."""
    if abs(n) < base:
        return f"{n} B"
    value = float(n)
    for unit in units:
        value /= base
        # Compare *after* rounding: 1023.97 KiB must print as "1.0 MiB", not "1024.0 KiB".
        if round(abs(value), precision) < base or unit == units[-1]:
            return f"{value:.{precision}f} {unit}"
    raise AssertionError("unreachable: the loop returns on its last unit")
