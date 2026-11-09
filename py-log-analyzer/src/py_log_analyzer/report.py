"""Render `Stats` as a plain-text report: a generator of lines; the caller decides where they go."""

import math
from collections import Counter
from collections.abc import Iterator, Sequence
from datetime import datetime, timedelta
from itertools import batched

from py_log_analyzer.parse import Intake
from py_log_analyzer.stats import MINUTE, Minute, Stats, incidents

BARS = " ▁▂▃▄▅▆▇█"


def duration(ms: float) -> str:
    if math.isnan(ms):
        return "-"
    return f"{ms:.0f} ms" if ms < 1000 else f"{ms / 1000:.1f} s"


def size(n: float) -> str:
    for unit in ("B", "KiB", "MiB", "GiB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TiB"


def sparkline(values: Sequence[float]) -> str:
    """Scale to the largest value; a non-zero value never rounds down to a blank."""
    top = max(values, default=0) or 1
    return "".join(BARS[max(1, round(v / top * (len(BARS) - 1)))] if v else BARS[0] for v in values)


def timeline(stats: Stats, width: int) -> tuple[list[int], list[int], timedelta]:
    """Requests and 5xx per column, with each column spanning a whole number of minutes."""
    assert stats.first and stats.last
    start = stats.first.replace(second=0)
    span = (stats.last.replace(second=0) - start) // MINUTE + 1
    # The smallest round step (in minutes) that fits the span into `width` columns.
    steps = (1, 2, 5, 10, 15, 30, 60, 120, 180, 360, 720, 1440)
    per_column = next((s for s in steps if s * width >= span), math.ceil(span / width))
    empty = Minute()
    series = [stats.minutes.get(start + i * MINUTE, empty) for i in range(span)]
    columns = list(batched(series, per_column, strict=False))  # 3.12+; the last chunk may be short
    return (
        [sum(m.hits for m in col) for col in columns],
        [sum(m.errors for m in col) for col in columns],
        per_column * MINUTE,
    )


def _every(step: timedelta) -> str:
    minutes = step // MINUTE
    if minutes % 60 == 0:
        return f"{minutes // 60} h"
    return f"{minutes} min"


def render(stats: Stats, intake: Intake, *, width: int = 72, min_hits: int = 20) -> Iterator[str]:
    skipped = f"  ({intake.rejected:,} unparseable lines skipped)" if intake.rejected else ""
    if not stats.requests:
        yield f"No requests found in {intake.lines:,} lines.{skipped}"
        return

    assert stats.first and stats.last
    tz = stats.first.tzinfo

    def local(t: datetime) -> datetime:  # show every time in the log's own zone
        return t.astimezone(tz)

    yield f"Window    {stats.first:%Y-%m-%d %H:%M} → {stats.last:%Y-%m-%d %H:%M} ({stats.first:%z})"
    yield f"Requests  {stats.requests:,}  ·  {size(stats.bytes)} sent{skipped}"
    classes = Counter[str]()
    for status, n in stats.statuses.items():
        classes[f"{status // 100}xx"] += n
    yield "Status    " + "   ".join(
        f"{name} {n / stats.requests:.2%}" for name, n in sorted(classes.items())
    )
    if stats.latency.count:
        q = stats.latency.quantile
        yield (
            f"Latency   p50 {duration(q(0.5))}   p95 {duration(q(0.95))}   "
            f"p99 {duration(q(0.99))}   max {duration(stats.latency.max)}"
        )

    hits, errors, step = timeline(stats, width)
    yield ""
    yield f"Traffic   {sparkline(hits)}  peak {max(hits):,}"
    yield f"5xx       {sparkline(errors)}  peak {max(errors):,}"
    yield f"          1 column = {_every(step)}"

    found = incidents(stats.minutes)
    yield ""
    yield f"Incidents (≥5 5xx a minute, ≥5% of traffic): {len(found) or 'none'}"
    for inc in found:
        yield (
            f"  {local(inc.start):%Y-%m-%d %H:%M} → {local(inc.end):%H:%M}  {inc.minutes} min  "
            f"{inc.errors:,}/{inc.hits:,} failed ({inc.errors / inc.hits:.0%})  "
            f"mostly {inc.culprit} ({inc.culprit_errors:,})"
        )

    if stats.latency.count:
        busy = {name: ep for name, ep in stats.endpoints.items() if ep.hits >= min_hits}
        ranked = sorted(busy.items(), key=lambda item: item[1].latency.quantile(0.95), reverse=True)
        name_width = max((len(name) for name, _ in ranked[: stats.top]), default=8)
        yield ""
        yield f"Slowest endpoints by p95 (≥{min_hits} hits)"
        yield (
            f"  {'endpoint':<{name_width}}  {'hits':>7}  {'5xx':>6}"
            f"  {'p50':>7}  {'p95':>7}  {'p99':>7}  {'max':>7}"
        )
        for name, ep in ranked[: stats.top]:
            q = ep.latency.quantile
            yield (
                f"  {name:<{name_width}}  {ep.hits:>7,}  {ep.error_rate:>6.1%}"
                f"  {duration(q(0.5)):>7}  {duration(q(0.95)):>7}  {duration(q(0.99)):>7}"
                f"  {duration(ep.latency.max):>7}"
            )

    yield ""
    yield "Top clients"
    for ip, n in stats.ips.most_common(stats.top):
        yield f"  {ip:<15}  {n:>7,}  {n / stats.requests:6.1%}"

    if stats.latency.count:
        yield ""
        yield "Slowest requests"
        for r in stats.slowest:
            yield (
                f"  {duration(r.ms or 0):>7}  {local(r.time):%Y-%m-%d %H:%M:%S}  {r.status}  "
                f"{r.method} {r.path}  ({r.ip})"
            )

    if intake.samples:
        yield ""
        yield "Unparseable lines (first few)"
        for line in intake.samples:
            yield f"  {line.source}:{line.number}: {shorten(line.text.rstrip())}"


def shorten(text: str, limit: int = 90) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"
