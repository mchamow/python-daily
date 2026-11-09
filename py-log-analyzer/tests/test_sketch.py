import math
import random

import pytest

from py_log_analyzer.sketch import Sketch


@pytest.fixture(scope="module")
def latencies() -> list[float]:
    rng = random.Random(7)
    return [rng.lognormvariate(math.log(80), 1.1) for _ in range(50_000)]


@pytest.mark.parametrize("q", [0.0, 0.5, 0.9, 0.95, 0.99, 0.999, 1.0])
def test_quantiles_within_one_percent_of_exact(latencies: list[float], q: float) -> None:
    sketch = Sketch(accuracy=0.01)
    for value in latencies:
        sketch.add(value)
    exact = sorted(latencies)[round(q * (len(latencies) - 1))]
    assert sketch.quantile(q) == pytest.approx(exact, rel=0.01)


def test_memory_is_bounded_by_range_not_count(latencies: list[float]) -> None:
    sketch = Sketch()
    for value in latencies * 4:  # 200,000 values
        sketch.add(value)
    span = math.log(max(latencies) / min(latencies)) / math.log(1.01 / 0.99)
    assert sketch.count == 200_000
    assert sketch.buckets <= span + 2


def test_zeros_and_empty() -> None:
    sketch = Sketch()
    assert math.isnan(sketch.quantile(0.5))
    for value in (0.0, 0.0, 0.0, 10.0):
        sketch.add(value)
    assert sketch.quantile(0.5) == 0.0
    assert sketch.quantile(1.0) == pytest.approx(10.0, rel=0.01)
    with pytest.raises(ValueError):
        sketch.quantile(1.5)
