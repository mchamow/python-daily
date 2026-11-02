"""Text bar charts for `cipher freq` and `cipher crack --explain`."""

from .analysis import (
    ENGLISH,
    ENGLISH_IOC,
    RANDOM_IOC,
    frequencies,
    index_of_coincidence,
    letters_only,
)
from .crack import Report

EIGHTHS = " ▏▎▍▌▋▊▉"  # partial blocks, so a bar can end mid-cell


def bar(value: float, full: float, width: int) -> str:
    """A bar `width` cells long at `value == full`, with 1/8-cell resolution."""
    eighths = round(max(0.0, min(value / full, 1.0)) * width * 8)
    whole, part = divmod(eighths, 8)
    return ("█" * whole + EIGHTHS[part].strip()).ljust(width)


def render_frequencies(text: str, width: int = 40) -> str:
    """One row per letter: this text's frequency as a bar, English's as a ┆ marker."""
    letters = letters_only(text)
    freqs = frequencies(text)
    full = max(*freqs.values(), *ENGLISH.values())
    rows = [f"{len(letters):,} letters, index of coincidence {index_of_coincidence(letters):.4f}"]
    rows.append(f"(English ≈ {ENGLISH_IOC:.4f}, random letters ≈ {RANDOM_IOC:.4f})  ┆ = English")
    # Both dicts are in a-z order; strict=True turns any mismatch into an error, not a silent cut.
    for (letter, pct), english in zip(freqs.items(), ENGLISH.values(), strict=True):
        cells = list(bar(pct, full, width))  # a str is immutable, a list of cells is not
        mark = min(round(english / full * width), width - 1)
        if cells[mark] == " ":
            cells[mark] = "┆"
        rows.append(f"  {letter} {pct:5.1f}% {''.join(cells)} {english:5.1f}%")
    return "\n".join(rows)


def render_key_lengths(report: Report, width: int = 30) -> str:
    """Mean index of coincidence per key length; the right length is the first tall bar."""
    low, high = RANDOM_IOC * 0.8, ENGLISH_IOC * 1.15  # zoom in on the interesting range
    rows = [
        "Key length vs. mean index of coincidence of its columns",
        f"(English ≈ {ENGLISH_IOC:.3f}, random ≈ {RANDOM_IOC:.3f})",
    ]
    for length, score in report.key_lengths.items():
        arrow = "  ← key length" if length == report.key_length else ""
        rows.append(f"  {length:>3}  {score:.4f}  {bar(score - low, high - low, width)}{arrow}")
    return "\n".join(row.rstrip() for row in rows)
