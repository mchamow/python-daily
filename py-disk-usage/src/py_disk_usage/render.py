"""Turn a ``Node`` tree into text lines, with a recursive generator and ``yield from``."""

from collections.abc import Iterator
from typing import Literal

from .scan import Node
from .size import Size

type Unit = Literal["h", "H"]  # the two presentation types Size.__format__ adds

BAR_WIDTH = 20
EIGHTHS = " ▏▎▍▌▋▊▉"  # partial blocks give a bar 8x the resolution of its width in characters


def bar(fraction: float, width: int = BAR_WIDTH) -> str:
    eighths = round(min(max(fraction, 0.0), 1.0) * width * 8)
    full, part = divmod(eighths, 8)
    return ("█" * full + EIGHTHS[part].strip()).ljust(width)


def share(part: int, whole: int) -> float:
    return part / whole if whole else 0.0


def row(size: Size, fraction: float, label: str, unit: Unit) -> str:
    # The format spec is itself an f-string: {unit} is filled in before Size.__format__ sees it.
    return f"{size:>10.1{unit}}  {bar(fraction)}  {fraction:>4.0%}  {label}"


def label(node: Node) -> str:
    if node.link is not None:
        return f"{node.name} -> {node.link}"
    if not node.is_dir:
        return node.name
    suffix = f"  [{node.error}]" if node.error else ""
    return f"{node.name.rstrip('/')}/{suffix}"


def render(root: Node, *, depth: int = 2, limit: int = 10, unit: Unit = "h") -> Iterator[str]:
    """The root line, then up to ``limit`` children per directory, ``depth`` levels deep.

    Bars and percentages are relative to the parent directory, like ncdu.
    """
    files = f"{root.files:,} file{'' if root.files == 1 else 's'}"
    yield row(root.size, 1.0, f"{label(root)}  ({files})", unit)
    yield from branch(root, depth, limit, unit, indent="")


def branch(parent: Node, depth: int, limit: int, unit: Unit, indent: str) -> Iterator[str]:
    if depth <= 0:
        return
    shown, hidden = parent.children[:limit], parent.children[limit:]
    for i, child in enumerate(shown):
        last = i == len(shown) - 1 and not hidden
        fraction = share(child.size, parent.size)
        yield row(child.size, fraction, f"{indent}{'└── ' if last else '├── '}{label(child)}", unit)
        # yield from: re-yield everything the sub-generator produces. Recursion, but lazy.
        yield from branch(child, depth - 1, limit, unit, indent + ("    " if last else "│   "))
    if hidden:
        rest = sum((c.size for c in hidden), start=Size(0))  # start= keeps the result a Size
        text = f"{indent}└── … {len(hidden)} more"
        yield row(rest, share(rest, parent.size), text, unit)
