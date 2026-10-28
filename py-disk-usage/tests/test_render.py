"""Bars and the tree layout."""

import pytest

from py_disk_usage.render import bar, render
from py_disk_usage.scan import Node
from py_disk_usage.size import Size


@pytest.mark.parametrize(
    ("fraction", "expected"),
    [
        (0.0, ""),
        (1.0, "█" * 20),
        (0.5, "█" * 10),
        (1 / 160, "▏"),  # one eighth of one cell
        (0.3, "██████"),
        (0.33, "██████▋"),  # 52.8 eighths round to 53: 6 full + 5/8
        (1.7, "█" * 20),  # clamped
    ],
)
def test_bar(fraction: float, expected: str) -> None:
    assert bar(fraction) == expected.ljust(20)


def dir_(name: str, *children: Node) -> Node:
    return Node(name, Size(sum(c.size for c in children)), is_dir=True, children=list(children))


def file_(name: str, size: int) -> Node:
    return Node(name, Size(size), files=1)


def test_tree_layout_depth_and_collapsing() -> None:
    root = dir_(
        "proj",
        dir_("src", file_("main.py", 3072), file_("util.py", 1024)),
        file_("a.bin", 2048),
        file_("b.bin", 1024),
        file_("c.bin", 1024),
    )
    root.files = 5
    lines = [line[34:].lstrip() for line in render(root, depth=2, limit=2)]  # after size + bar
    assert lines == [
        "100%  proj/  (5 files)",
        "50%  ├── src/",
        "75%  │   ├── main.py",
        "25%  │   └── util.py",
        "25%  ├── a.bin",
        "25%  └── … 2 more",
    ]
    assert len(list(render(root, depth=0))) == 1
    assert next(render(root)).startswith("   8.0 KiB  ████████████████████")
