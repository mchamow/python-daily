"""The scandir tree and the os.walk stream, on small trees built in tmp_path."""

import os
import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import NoReturn

import pytest

from py_disk_usage.scan import Node, Options, Problem, scan
from py_disk_usage.walk import iter_files, largest

APPARENT = Options(apparent=True)


def no_problems(problem: Problem) -> NoReturn:
    pytest.fail(f"unexpected {problem}")


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """root/ big.bin (5000)  docs/a.txt (300)  docs/deep/b.txt (200)  .git/objects (1000)"""
    (tmp_path / "docs" / "deep").mkdir(parents=True)
    (tmp_path / ".git").mkdir()
    (tmp_path / "big.bin").write_bytes(b"x" * 5000)
    (tmp_path / "docs" / "a.txt").write_bytes(b"a" * 300)
    (tmp_path / "docs" / "deep" / "b.txt").write_bytes(b"b" * 200)
    (tmp_path / ".git" / "objects").write_bytes(b"o" * 1000)
    return tmp_path


def leaves(node: Node) -> Iterator[Node]:
    if not node.is_dir:
        yield node
    for child in node.children:
        yield from leaves(child)


def child(node: Node, name: str) -> Node:
    return next(c for c in node.children if c.name == name)


def test_totals_counts_and_order(tree: Path) -> None:
    root = scan(tree, APPARENT).root
    assert sum(f.size for f in leaves(root)) == 6500
    assert root.files == 4
    assert [c.name for c in root.children] == ["big.bin", ".git", "docs"]  # biggest first
    docs = child(root, "docs")
    assert docs.size == 500 + docs_own_sizes(tree)
    assert child(docs, "deep").files == 1


def docs_own_sizes(tree: Path) -> int:
    return sum(p.lstat().st_size for p in (tree / "docs", tree / "docs" / "deep"))


def test_hard_links_are_counted_once(tree: Path) -> None:
    os.link(tree / "big.bin", tree / "docs" / "same-bytes.bin")
    root = scan(tree, APPARENT).root
    assert sum(f.size for f in leaves(root)) == 6500
    assert root.files == 5  # still listed: it's a second name, just not a second copy
    assert sum(f.size for f in iter_files(tree, APPARENT, no_problems)) == 6500


def test_symlinks_are_counted_not_followed(tree: Path) -> None:
    (tree / "shortcut").symlink_to(tree / "docs", target_is_directory=True)
    link = child(scan(tree, APPARENT).root, "shortcut")
    assert link.link == str(tree / "docs")
    assert link.size == (tree / "shortcut").lstat().st_size  # the link itself, a few bytes
    assert link.children == []


def test_exclude_prunes_both_engines(tree: Path) -> None:
    options = Options(apparent=True, exclude=(".git", "*.bin"))
    root = scan(tree, options).root
    assert [c.name for c in root.children] == ["docs"]
    walked = sorted(os.path.relpath(f.path, tree) for f in iter_files(tree, options, no_problems))
    assert walked == [os.path.join("docs", "a.txt"), os.path.join("docs", "deep", "b.txt")]


def test_scandir_tree_and_walk_stream_agree(tree: Path) -> None:
    tree_files = {f.name: f.size for f in leaves(scan(tree).root)}
    walk_files = {Path(f.path).name: f.size for f in iter_files(tree, Options(), no_problems)}
    assert tree_files == walk_files
    top = largest(tree, 2, APPARENT, no_problems)  # apparent: on disk, 1000 and 300 B tie at 4 KiB
    assert [(Path(f.path).name, f.size) for f in top] == [("big.bin", 5000), ("objects", 1000)]


@pytest.mark.skipif(sys.platform == "win32" or os.geteuid() == 0, reason="needs POSIX non-root")
def test_unreadable_directory_is_a_problem_not_a_crash(tree: Path) -> None:
    locked = tree / "docs" / "deep"
    locked.chmod(0)
    try:
        result = scan(tree, APPARENT)
        walked: list[Problem] = []
        names = {Path(f.path).name for f in iter_files(tree, APPARENT, walked.append)}
    finally:
        locked.chmod(0o755)  # or pytest can't clean tmp_path up
    assert child(child(result.root, "docs"), "deep").error == "Permission denied"
    assert result.root.files == 3  # everything else still counted
    assert [p.path for p in result.problems] == [str(locked)]
    assert [p.path for p in walked] == [str(locked)]
    assert names == {"big.bin", "a.txt", "objects"}


def test_generator_errors_are_lazy(tmp_path: Path) -> None:
    files = iter_files(tmp_path / "missing", Options(), no_problems)  # no error yet!
    with pytest.raises(FileNotFoundError):
        next(files)


@pytest.mark.skipif(shutil.which("du") is None, reason="needs du")
def test_on_disk_total_matches_du(tree: Path) -> None:
    os.link(tree / "big.bin", tree / "hard.bin")
    (tree / "shortcut").symlink_to("big.bin")
    du = subprocess.run(["du", "-sk", tree], capture_output=True, text=True, check=True)
    kib = int(du.stdout.split()[0])
    assert -(-scan(tree).root.size // 1024) == kib  # ceiling division, as du rounds up
