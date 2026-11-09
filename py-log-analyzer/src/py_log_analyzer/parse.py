"""Turn raw access-log lines into `Request`s: the combined log format, plus nginx's request time.

    203.0.113.7 - - [08/Nov/2026:14:07:12 +0100] "GET /api/cart HTTP/1.1" 200 512 "-" "curl/8" 0.031

The trailing request time (nginx `$request_time`, in seconds) is optional. Apache's plain
combined format has none, and then the report simply has no latency section.
"""

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from py_log_analyzer.source import Line

LINE = re.compile(
    r"""
    (?P<ip>\S+) \s \S+ \s \S+ \s                          # client, identd, user
    \[ (?P<minute>\d\d/\w{3}/\d{4}:\d\d:\d\d)             # 08/Nov/2026:14:07
       :(?P<second>\d\d) \s (?P<offset>[+-]\d{4}) \] \s   # :12 +0100
    "(?P<method>[A-Z]+) \s (?P<path>\S+) \s HTTP/[\d.]+" \s
    (?P<status>\d{3}) \s (?P<size>\d+|-)
    # A quoted string where \" is an escaped quote, written as an "unrolled loop": runs of plain
    # characters, then (escape + run)*. 4x faster than (?:[^"\\]|\\.)*, one step per character.
    (?: \s "[^"\\]*(?:\\.[^"\\]*)*"                       # referer
        \s "(?P<agent>[^"\\]*(?:\\.[^"\\]*)*)" )?         # user agent
    (?: \s (?P<seconds>\d+(?:\.\d+)?) )?                  # nginx $request_time
    \s*$
    """,
    re.VERBOSE | re.ASCII,  # ASCII: \d means [0-9] and \w means [A-Za-z0-9_], not all of Unicode
)

# IDs in URL paths: numbers, UUIDs and long hex strings, one whole path segment each.
_ID = re.compile(
    r"(?<=/)(?:\d+|[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}|[0-9a-f]{16,})(?=/|$)",
    re.ASCII | re.IGNORECASE,
)

# Not strptime's %b: that follows the process locale, so after locale.setlocale(LC_ALL, "")
# on a Polish machine it expects "lis", not "Nov". Log timestamps are always English.
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_MONTH_NUMBER = {name: n for n, name in enumerate(MONTHS, start=1)}


@dataclass(slots=True)  # not frozen: a frozen dataclass's __init__ is ~3x slower, per line
class Request:
    ip: str
    time: datetime
    method: str
    path: str
    status: int
    size: int
    agent: str
    ms: float | None  # None when the log has no request-time field

    @property
    def endpoint(self) -> str:
        return f"{self.method} {endpoint(self.path)}"


@dataclass(slots=True)
class Intake:
    """What the parse stage saw: every line counted, unparseable ones sampled."""

    lines: int = 0
    rejected: int = 0
    samples: list[Line] = field(default_factory=list)

    def reject(self, line: Line, keep: int = 3) -> None:
        self.rejected += 1
        if len(self.samples) < keep:
            self.samples.append(line)


def endpoint(path: str) -> str:
    """'/api/orders/1842/pay?retry=1' -> '/api/orders/{id}/pay'"""
    return _ID.sub("{id}", path.partition("?")[0])


@lru_cache(maxsize=2048)
def _minute(stamp: str, offset: str) -> datetime:
    """'08/Nov/2026:14:07' and '+0100' -> an aware datetime.

    Every line logged in the same minute shares the answer, so with the cache this runs once a
    minute instead of once a line. lru_cache hands back the *same* object each time, which is
    safe only because datetime is immutable.
    """
    day, month, rest = stamp.split("/")
    year, hour, minute = rest.split(":")
    sign = -1 if offset[0] == "-" else 1
    tz = timezone(sign * timedelta(hours=int(offset[1:3]), minutes=int(offset[3:5])))
    return datetime(int(year), _MONTH_NUMBER[month], int(day), int(hour), int(minute), tzinfo=tz)


def parse_line(text: str) -> Request | None:
    if (m := LINE.match(text)) is None:
        return None
    try:
        time = _minute(m["minute"], m["offset"]).replace(second=int(m["second"]))
    except KeyError, ValueError:  # "Foo" as a month, 31/Feb, a +2500 offset (PEP 758 syntax)
        return None
    size, seconds = m["size"], m["seconds"]
    return Request(
        ip=m["ip"],
        time=time,
        method=m["method"],
        path=m["path"],
        status=int(m["status"]),
        size=0 if size == "-" else int(size),
        agent=m["agent"] or "",
        ms=None if seconds is None else float(seconds) * 1000,
    )


def parse(lines: Iterable[Line], intake: Intake) -> Iterator[Request]:
    """Lazily parse; lines that don't fit are tallied in `intake` instead of stopping the run."""
    for line in lines:
        intake.lines += 1
        if (request := parse_line(line.text)) is None:
            intake.reject(line)
        else:
            yield request
