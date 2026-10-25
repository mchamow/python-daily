"""Due dates people actually type ('fri', '+3d', 'tomorrow') and how to show them back.

``today`` is always a parameter rather than a call to ``date.today()``, so tests can pin it.
"""

import re
from datetime import date, timedelta

_WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
_OFFSET = re.compile(r"\+(?P<n>\d+)(?P<unit>[dw])")


def parse_due(text: str, today: date) -> date:
    word = text.strip().lower()
    match word:
        case "today":
            return today
        case "tomorrow" | "tmr":
            return today + timedelta(days=1)
        case _ if len(word) >= 3 and (day := _weekday(word)) is not None:
            # The next such weekday, strictly after today: 'fri' on a Friday means next week.
            return today + timedelta(days=(day - today.weekday() - 1) % 7 + 1)
        case _ if offset := _OFFSET.fullmatch(word):
            days = int(offset["n"]) * (7 if offset["unit"] == "w" else 1)
            return today + timedelta(days=days)
    try:
        return date.fromisoformat(word)
    except ValueError:
        raise ValueError(
            f"can't read due date {text!r}: use YYYY-MM-DD, today, tomorrow, a weekday or +3d"
        ) from None


def _weekday(word: str) -> int | None:
    return next((i for i, name in enumerate(_WEEKDAYS) if name.startswith(word)), None)


def describe_due(due: date, today: date) -> str:
    match (due - today).days:
        case 0:
            return "today"
        case 1:
            return "tomorrow"
        case days if days < 0:
            return f"overdue {-days}d"
        case days if days < 7:
            return _WEEKDAYS[due.weekday()][:3]
        case _:
            return due.isoformat()
