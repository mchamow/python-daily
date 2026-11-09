"""Percentiles in constant memory: a log-bucketed histogram (the idea behind DDSketch).

An exact p99 needs every value kept and sorted: O(n) memory, which is exactly what a streaming
analyzer can't afford. Instead, each value goes into a bucket whose bounds grow geometrically,
(gamma**(k-1), gamma**k], and only the bucket counts are kept. Any quantile then comes back within
`accuracy` *relative* error (1% by default), and 1 ms…10 min needs only ~660 buckets at most.
"""

import math
from collections import Counter
from dataclasses import dataclass, field


@dataclass(slots=True)
class Sketch:
    accuracy: float = 0.01
    count: int = 0
    max: float = 0.0
    zeros: int = 0  # 0.000 s is common in logs and log(0) is undefined, so count it apart
    _buckets: Counter[int] = field(default_factory=Counter, repr=False)
    _gamma: float = field(init=False, repr=False)
    _log_gamma: float = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not 0 < self.accuracy < 1:
            raise ValueError(f"accuracy must be between 0 and 1, got {self.accuracy}")
        self._gamma = (1 + self.accuracy) / (1 - self.accuracy)
        self._log_gamma = math.log(self._gamma)

    def add(self, value: float) -> None:
        self.count += 1
        if value <= 0:
            self.zeros += 1
            return
        self.max = max(self.max, value)
        self._buckets[math.ceil(math.log(value) / self._log_gamma)] += 1

    def quantile(self, q: float) -> float:
        """The value at rank round(q·(n-1)) in sorted order, within `accuracy` relative error."""
        if not 0 <= q <= 1:
            raise ValueError(f"q must be between 0 and 1, got {q}")
        if self.count == 0:
            return math.nan
        rank = round(q * (self.count - 1))
        seen = self.zeros
        if rank < seen:
            return 0.0
        for k in sorted(self._buckets):
            seen += self._buckets[k]
            if rank < seen:
                # The midpoint (in relative terms) of (gamma**(k-1), gamma**k].
                return min(2 * self._gamma**k / (self._gamma + 1), self.max)
        return self.max  # unreachable: the buckets hold every non-zero value

    @property
    def buckets(self) -> int:
        return len(self._buckets)
