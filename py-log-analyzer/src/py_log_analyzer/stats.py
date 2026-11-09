"""One pass, many answers: fold a stream of requests into every aggregate the report needs.

A generator can be iterated once. So instead of `top_ips(requests)`, `slowest(requests)`, …
(each of which would need its own pass, i.e. its own read of a 2 GB file), every request is fed
to `Stats.add` exactly once, and each aggregate is kept in memory that doesn't grow with the log.
"""

import heapq
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from py_log_analyzer.parse import Request
from py_log_analyzer.sketch import Sketch

MINUTE = timedelta(minutes=1)


@dataclass(slots=True)
class Endpoint:
    hits: int = 0
    errors: int = 0  # 5xx only: a 404 is the client's problem, a 503 is yours
    latency: Sketch = field(default_factory=Sketch)

    @property
    def error_rate(self) -> float:
        return self.errors / self.hits if self.hits else 0.0


@dataclass(slots=True)
class Minute:
    hits: int = 0
    errors: int = 0
    failing: Counter[str] = field(default_factory=Counter)  # endpoint -> 5xx count


@dataclass(frozen=True, slots=True)
class Incident:
    start: datetime
    end: datetime  # exclusive: the minute after the last bad one
    hits: int
    errors: int
    culprit: str
    culprit_errors: int

    @property
    def minutes(self) -> int:
        return (self.end - self.start) // MINUTE


@dataclass
class Stats:
    top: int = 5
    requests: int = 0
    bytes: int = 0
    first: datetime | None = None
    last: datetime | None = None
    statuses: Counter[int] = field(default_factory=Counter)
    ips: Counter[str] = field(default_factory=Counter)
    endpoints: defaultdict[str, Endpoint] = field(default_factory=lambda: defaultdict(Endpoint))
    minutes: defaultdict[datetime, Minute] = field(default_factory=lambda: defaultdict(Minute))
    latency: Sketch = field(default_factory=Sketch)
    # A min-heap of the `top` slowest so far: the root is the fastest of them, the one to evict.
    _slowest: list[tuple[float, int, Request]] = field(default_factory=list)

    def add(self, r: Request) -> None:
        self.requests += 1
        self.bytes += r.size
        # Rotated files can be passed in any order, so track min/max rather than first/last seen.
        if self.first is None or r.time < self.first:
            self.first = r.time
        if self.last is None or r.time > self.last:
            self.last = r.time
        self.statuses[r.status] += 1
        self.ips[r.ip] += 1

        name = r.endpoint
        ep = self.endpoints[name]
        minute = self.minutes[r.time.replace(second=0)]
        ep.hits += 1
        minute.hits += 1
        if r.status >= 500:
            ep.errors += 1
            minute.errors += 1
            minute.failing[name] += 1

        if r.ms is not None:
            ep.latency.add(r.ms)
            self.latency.add(r.ms)
            # The middle element breaks ties: without it, two equal times would make heapq
            # compare two Requests, and dataclasses without order=True raise TypeError.
            entry = (r.ms, self.requests, r)
            if len(self._slowest) < self.top:
                heapq.heappush(self._slowest, entry)
            elif r.ms > self._slowest[0][0]:
                heapq.heapreplace(self._slowest, entry)

    @property
    def slowest(self) -> list[Request]:
        return [r for _, _, r in sorted(self._slowest, reverse=True)]

    @property
    def errors(self) -> int:
        return sum(n for status, n in self.statuses.items() if status >= 500)


def analyze(requests: Iterable[Request], top: int = 5) -> Stats:
    stats = Stats(top=top)
    for request in requests:  # the only loop that actually pulls on the pipeline
        stats.add(request)
    return stats


def incidents(
    minutes: Mapping[datetime, Minute], min_errors: int = 5, min_rate: float = 0.05
) -> list[Incident]:
    """Runs of consecutive minutes with ≥ `min_errors` 5xx making up ≥ `min_rate` of traffic."""
    bad = sorted(
        t for t, m in minutes.items() if m.errors >= min_errors and m.errors / m.hits >= min_rate
    )
    runs: list[list[datetime]] = []
    for t in bad:
        if runs and t - runs[-1][-1] == MINUTE:
            runs[-1].append(t)
        else:
            runs.append([t])

    found = []
    for run in runs:
        window = [minutes[t] for t in run]
        failing = sum((m.failing for m in window), Counter[str]())  # Counters add up
        [(culprit, culprit_errors)] = failing.most_common(1)
        found.append(
            Incident(
                start=run[0],
                end=run[-1] + MINUTE,
                hits=sum(m.hits for m in window),
                errors=sum(m.errors for m in window),
                culprit=culprit,
                culprit_errors=culprit_errors,
            )
        )
    return found
