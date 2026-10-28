"""Size.__format__: the h/H presentation types, and everything else falling through to int."""

import pytest

from py_disk_usage.size import Size


@pytest.mark.parametrize(
    ("value", "spec", "expected"),
    [
        (0, "h", "0 B"),
        (1023, "h", "1023 B"),
        (1536, "h", "1.5 KiB"),
        (1_572_864, ".2h", "1.50 MiB"),
        (1_572_864, "H", "1.6 MB"),
        (1_048_575, "h", "1.0 MiB"),  # rounds to 1024.0 KiB, so it must move up a unit
        (5 * 1024**7, "h", "5120.0 EiB"),  # past the last unit: keep growing, don't crash
        (1536, ">10h", "   1.5 KiB"),
        (1536, "<10h", "1.5 KiB   "),
        (1536, "*^11.0h", "***2 KiB***"),
        (1_572_864, ",", "1,572,864"),  # not ours: int handles it
        (255, "08b", "11111111"),
    ],
)
def test_format(value: int, spec: str, expected: str) -> None:
    assert format(Size(value), spec) == expected


def test_arithmetic_and_str_stay_sizes() -> None:
    total = sum([Size(1024), Size(512)])  # 0 + Size(1024) -> Size.__radd__
    assert isinstance(total, Size)
    assert f"{total + 512:h}" == "2.0 KiB"
    assert str(total) == f"{total}" == "1536"
    assert repr(total) == "Size(1536)"
    with pytest.raises(ValueError, match="Unknown format code 'h'"):
        f"{int(total):h}"
