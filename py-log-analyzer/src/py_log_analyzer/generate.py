"""loggen: an endless, deterministic stream of realistic nginx access-log lines.

The traffic has a daily rhythm, a scraper bot, a vulnerability scanner, the odd unparseable line,
and one planted outage: on 2026-11-08 from 14:07 to 14:20 (+01:00) the payment upstream is down,
checkout returns 503/504, and clients retry. `logscan` should find it on its own.

    uv run loggen -n 1000000 --rate 300 | uv run logscan -
    uv run loggen --samples data      # regenerate the bundled sample files
"""

import argparse
import io
import math
import os
import random
import sys
from collections.abc import Iterator
from compression import gzip, zstd
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from itertools import groupby, islice, takewhile
from pathlib import Path
from uuid import UUID

from py_log_analyzer.parse import MONTHS

TZ = timezone(timedelta(hours=1))  # CET
START = datetime(2026, 11, 7, tzinfo=TZ)
OUTAGE = (datetime(2026, 11, 8, 14, 7, tzinfo=TZ), datetime(2026, 11, 8, 14, 20, tzinfo=TZ))
BOT, SCANNER, OFFICE = "203.0.113.66", "198.51.100.13", "192.0.2.10"
AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 15_6) AppleWebKit/605.1.15 Version/26.1 Safari/605",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/142.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 26_1 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
    "Mozilla/5.0 (X11; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0",
    'okhttp/5.1.0 (Android 16; "Pixel 10")',  # a quote inside a user agent, escaped in the log
]
AGENT_IPS = [f"{net}.{n}" for net in ("192.0.2", "198.51.100", "203.0.113") for n in range(1, 255)]
SCAN_PATHS = ["/wp-login.php", "/.env", "/.git/config", "/phpmyadmin/", "/admin/config.php"]


@dataclass(frozen=True, slots=True)
class Route:
    method: str
    path: str  # {n} = a number, {uuid}, {hash}
    weight: float
    median_ms: float
    size: int
    spread: float = 0.6  # sigma of the lognormal latency: bigger = a longer tail


ROUTES = [
    Route("GET", "/", 14, 22, 18_400),
    Route("GET", "/products/{n}", 22, 38, 24_100),
    Route("GET", "/api/search?q={n}", 9, 160, 6_200, spread=0.9),
    Route("GET", "/api/cart", 10, 28, 1_100),
    Route("POST", "/api/cart/items", 5, 44, 300),
    Route("POST", "/api/checkout", 3, 320, 700),
    Route("POST", "/api/orders/{n}/pay", 2, 410, 500),
    Route("GET", "/api/orders/{n}", 4, 55, 2_300),
    Route("GET", "/api/users/{uuid}/avatar", 6, 18, 31_000),
    Route("POST", "/api/login", 3, 115, 400),
    Route("GET", "/static/app.{hash}.js", 16, 3, 412_000, spread=0.3),
    Route("GET", "/healthz", 5, 1, 2, spread=0.2),
    Route("GET", "/reports/export.csv", 0.2, 2_600, 4_800_000, spread=0.5),
]
PAYMENT = {"/api/checkout", "/api/orders/{n}/pay"}
WEIGHTS = [r.weight for r in ROUTES]


def _stamp(t: datetime) -> str:
    # Not %b: strftime's month names follow the locale, and log files are always English.
    return f"{t.day:02}/{MONTHS[t.month - 1]}/{t.year}:{t:%H:%M:%S %z}"


def _traffic(t: datetime) -> float:
    """Relative request rate: 0.3x at 04:00, 1.7x at 16:00, averaging 1."""
    hour = t.hour + t.minute / 60
    return 0.3 + 1.4 * (1 - math.cos(2 * math.pi * (hour - 4) / 24)) / 2


def _line(rng: random.Random, t: datetime, outage: bool, retry: bool = False) -> str:
    roll = rng.random()
    if roll < 0.0003:  # a TLS handshake sent to the plain-HTTP port: nginx logs the raw bytes
        handshake = r"\x16\x03\x01\x02\x00\x01"
        return f'{rng.choice(AGENT_IPS)} - - [{_stamp(t)}] "{handshake}" 400 157 "-" "-" 0.001'
    if roll < 0.0004:  # rotation mid-write: a line cut short
        return f'{rng.choice(AGENT_IPS)} - - [{_stamp(t)}] "GET /api/ca'

    if retry:
        ip, agent, route = rng.choice(AGENT_IPS), rng.choice(AGENTS), ROUTES[5]
    elif roll < 0.12:
        ip, agent = BOT, "Scrapy/2.13 (+https://scrapy.org)"
        route = ROUTES[1]
    elif roll < 0.128:
        ip, agent, route = SCANNER, "Mozilla/5.0 zgrab/0.x", None
    else:
        ip = OFFICE if roll < 0.16 else rng.choice(AGENT_IPS)
        agent = rng.choice(AGENTS)
        if rng.random() < 0.0005:
            agent += " \udcff"  # one invalid UTF-8 byte (0xff), written via surrogateescape
        route = rng.choices(ROUTES, WEIGHTS)[0]

    if route is None:
        method, path, status, size, ms = "GET", rng.choice(SCAN_PATHS), 404, 153, rng.uniform(1, 4)
    else:
        method, size = route.method, int(route.size * rng.uniform(0.7, 1.3))
        path = route.path.format(
            n=rng.randrange(1, 90_000), uuid=UUID(int=rng.getrandbits(128)), hash="3f2a9c1b"
        )
        ms = rng.lognormvariate(math.log(route.median_ms), route.spread)
        status = 200
        if route.path.startswith("/static/") and rng.random() < 0.5:
            status, size = 304, 0
        elif route.path == "/api/login" and rng.random() < 0.1:
            status, size = 401, 61
        elif route.path in PAYMENT and outage and rng.random() < 0.88:
            status, size = (503, 162) if rng.random() < 0.7 else (504, 167)
            ms = rng.uniform(5, 30) if status == 503 else rng.uniform(10_000, 10_400)
        elif rng.random() < 0.0015:
            status, size = 500, 177

    referer = "-" if rng.random() < 0.6 else "https://shop.example/"
    agent = agent.replace('"', '\\"')
    return (
        f'{ip} - - [{_stamp(t)}] "{method} {path} HTTP/1.1" {status} {size} '
        f'"{referer}" "{agent}" {ms / 1000:.3f}'
    )


def stream(
    seed: int = 12, rate: float = 12, start: datetime = START
) -> Iterator[tuple[datetime, str]]:
    """(time, line) pairs forever, `rate` requests a minute on average, in time order."""
    rng = random.Random(seed)
    t = start
    per_second = rate / 60
    while True:
        t += timedelta(seconds=rng.expovariate(per_second * _traffic(t)))
        outage = OUTAGE[0] <= t < OUTAGE[1]
        yield t, _line(rng, t, outage)
        if outage:  # every request during the outage drags a checkout retry along with it
            yield t, _line(rng, t, outage, retry=True)


def write_samples(directory: Path, seed: int = 12) -> list[Path]:
    """Three days, rotated the way logrotate leaves them: zstd, gzip, then today's plain file."""
    end = datetime(2026, 11, 9, 11, tzinfo=TZ)
    directory.mkdir(parents=True, exist_ok=True)
    names = {7: "access.log.2.zst", 8: "access.log.1.gz", 9: "access.log"}
    days = groupby(takewhile(lambda e: e[0] < end, stream(seed)), key=lambda e: e[0].day)
    for day, entries in days:
        path = directory / names[day]
        if path.suffix == ".zst":
            out: io.BufferedIOBase = zstd.open(path, "wb")
        elif path.suffix == ".gz":
            out = gzip.GzipFile(path, "wb", mtime=0)  # mtime=0: same bytes on every run
        else:
            out = path.open("wb")
        with out:
            out.writelines(f"{text}\n".encode(errors="surrogateescape") for _, text in entries)
    return [directory / name for name in names.values()]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="loggen", description=__doc__.splitlines()[0])
    p.add_argument("-n", "--lines", type=int, help="stop after N lines (default: never)")
    p.add_argument("--rate", type=float, default=12, help="average requests a minute (default 12)")
    p.add_argument("--seed", type=int, default=12)
    p.add_argument("--samples", type=Path, metavar="DIR", help="write the 3 sample files to DIR")
    args = p.parse_args(argv)

    if args.samples:
        for path in write_samples(args.samples, args.seed):
            print(f"wrote {path} ({path.stat().st_size:,} bytes)")
        return 0

    out = sys.stdout.buffer
    try:
        for _, text in islice(stream(args.seed, args.rate), args.lines):
            out.write(f"{text}\n".encode(errors="surrogateescape"))
        out.flush()
    except BrokenPipeError, KeyboardInterrupt:  # `loggen | head`, or Ctrl-C on an endless run
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
    return 0
