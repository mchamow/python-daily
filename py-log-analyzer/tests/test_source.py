from collections.abc import Callable
from compression import bz2, gzip, lzma, zstd
from pathlib import Path

import pytest

from py_log_analyzer.source import Codec, read_lines, sniff

CONTENT = "first line\nsecond line, caf\xc3\xa9\nbad byte \xff here\n".encode("latin-1")

WRITERS: dict[Codec, Callable[[Path, bytes], object]] = {
    "plain": Path.write_bytes,
    "gzip": lambda p, data: p.write_bytes(gzip.compress(data)),
    "bzip2": lambda p, data: p.write_bytes(bz2.compress(data)),
    "xz": lambda p, data: p.write_bytes(lzma.compress(data)),
    "zstd": lambda p, data: p.write_bytes(zstd.compress(data)),
}


@pytest.mark.parametrize("codec", list(WRITERS))
def test_every_codec_reads_the_same_text(tmp_path: Path, codec: Codec) -> None:
    path = tmp_path / "access.log"  # same name every time: the bytes decide, not the extension
    WRITERS[codec](path, CONTENT)
    assert sniff(path) == codec
    texts = [line.text for line in read_lines([str(path)])]
    assert texts == ["first line\n", "second line, café\n", "bad byte \\xff here\n"]


def test_lines_chain_across_files_with_their_origin(tmp_path: Path) -> None:
    a, b = tmp_path / "a.log", tmp_path / "b.log.gz"
    a.write_text("1\n2\n")
    b.write_bytes(gzip.compress(b"3\n"))
    origins = [(Path(line.source).name, line.number) for line in read_lines([str(a), str(b)])]
    assert origins == [("a.log", 1), ("a.log", 2), ("b.log.gz", 1)]
