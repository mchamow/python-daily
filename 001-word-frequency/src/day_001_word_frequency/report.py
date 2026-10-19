"""Rendering results as aligned text charts or JSON."""

import json
from collections import Counter
from collections.abc import Mapping, Sequence

from .analysis import Distinctive

BAR = "█"


def summary(per_doc: Mapping[str, Counter[str]], scanned: int, counted: Counter[str]) -> str:
    files = len(per_doc)
    return (
        f"Scanned {files} file{'s' if files != 1 else ''} · {scanned:,} words · "
        f"{counted.total():,} counted · {len(counted):,} distinct"
    )


def bar_chart(rows: Sequence[tuple[str, int]], *, width: int = 32) -> str:
    """Ranked rows with bars scaled to the largest count."""
    if not rows:
        return "  (no words left after filtering)"
    biggest = rows[0][1]
    word_width = max(len(word) for word, _ in rows)
    rank_width = len(str(len(rows)))
    return "\n".join(
        # Format specs can nest: {word:<{word_width}} pads to a width computed at runtime.
        f"  {rank:>{rank_width}}  {word:<{word_width}}  {count:>6,}  "
        f"{BAR * max(1, round(count / biggest * width))}"
        for rank, (word, count) in enumerate(rows, start=1)
    )


def distinctive_chart(results: Mapping[str, list[Distinctive]]) -> str:
    blocks = []
    for name, items in results.items():
        word_width = max((len(d.word) for d in items), default=0)
        lines = [f"{name}"] + [
            f"  {d.word:<{word_width}}  {d.lift:>6.1f}\N{MULTIPLICATION SIGN}  ({d.count} times)"
            for d in items
        ]
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def as_json(
    per_doc: Mapping[str, Counter[str]], scanned: int, counted: Counter[str], top: int
) -> str:
    return json.dumps(
        {
            "files": list(per_doc),
            "words_scanned": scanned,
            "words_counted": counted.total(),
            "distinct": len(counted),
            "top": [{"word": w, "count": n} for w, n in counted.most_common(top)],
        },
        indent=2,
        ensure_ascii=False,
    )
