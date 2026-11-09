from datetime import datetime, timedelta, timezone

import pytest

from py_log_analyzer.parse import Intake, endpoint, parse, parse_line
from py_log_analyzer.source import Line

NGINX = (
    '203.0.113.7 - - [08/Nov/2026:14:07:12 +0100] "POST /api/checkout?retry=1 HTTP/1.1" 503 162 '
    '"https://shop.example/" "okhttp/5.1.0 (Android 16; \\"Pixel 10\\")" 0.031\n'
)


def test_parses_nginx_line_with_escaped_quote_and_request_time() -> None:
    r = parse_line(NGINX)
    assert r is not None
    assert r.ip == "203.0.113.7"
    assert r.time == datetime(2026, 11, 8, 14, 7, 12, tzinfo=timezone(timedelta(hours=1)))
    assert (r.method, r.status, r.size) == ("POST", 503, 162)
    assert r.agent == 'okhttp/5.1.0 (Android 16; \\"Pixel 10\\")'
    assert r.ms == pytest.approx(31.0)
    assert r.endpoint == "POST /api/checkout"


def test_apache_combined_and_common_formats_have_no_latency() -> None:
    combined = '10.0.0.1 - bob [01/Jan/2026:00:00:00 -0500] "GET / HTTP/1.0" 200 - "-" "curl/8"'
    common = '10.0.0.1 - - [01/Jan/2026:00:00:00 +0000] "GET /a HTTP/1.1" 404 9'
    for text in (combined, common):
        r = parse_line(text)
        assert r is not None
        assert r.ms is None
    assert parse_line(combined).size == 0  # type: ignore[union-attr]


@pytest.mark.parametrize(
    "text",
    [
        '1.2.3.4 - - [07/Nov/2026:00:35:50 +0100] "\\x16\\x03\\x01" 400 157 "-" "-" 0.001',  # TLS
        '1.2.3.4 - - [07/Nov/2026:13:54:58 +0100] "GET /api/ca',  # truncated
        '1.2.3.4 - - [07/Foo/2026:13:54:58 +0100] "GET / HTTP/1.1" 200 1',  # unknown month
        '1.2.3.4 - - [31/Feb/2026:13:54:58 +0100] "GET / HTTP/1.1" 200 1',  # no such date
        "",
    ],
)
def test_unparseable_lines_return_none(text: str) -> None:
    assert parse_line(text) is None


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/api/orders/1842/pay?retry=1", "/api/orders/{id}/pay"),
        ("/api/users/9f1c2a3b-0c4d-4e5f-8a9b-0c1d2e3f4a5b/avatar", "/api/users/{id}/avatar"),
        ("/blobs/0123456789abcdef0123", "/blobs/{id}"),
        ("/static/app.3f2a9c1b.js", "/static/app.3f2a9c1b.js"),  # part of a segment: kept
        ("/v2/items", "/v2/items"),
    ],
)
def test_endpoint_collapses_ids(path: str, expected: str) -> None:
    assert endpoint(path) == expected


def test_parse_is_lazy_and_tallies_rejects() -> None:
    lines = [Line("x.log", n, text) for n, text in enumerate([NGINX, "junk\n", NGINX], 1)]
    intake = Intake()
    requests = parse(lines, intake)
    assert intake.lines == 0  # nothing has run yet: a generator starts on the first next()
    assert len(list(requests)) == 2
    assert (intake.lines, intake.rejected) == (3, 1)
    assert intake.samples[0].number == 2
    assert list(requests) == []  # and a generator is spent after one pass
