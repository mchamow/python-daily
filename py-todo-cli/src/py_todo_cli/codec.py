"""Dataclasses <-> JSON, with the standard library only.

``json`` only knows dicts, lists, str, int, float, bool and None. Encoding is easy: a
``default=`` hook turns dataclasses and dates into things json does know. Decoding back into
*typed* objects is what System.Text.Json does for you and Python's stdlib doesn't, so this module
is a small, strict decoder driven by the dataclass's own type hints.
"""

import json
from dataclasses import MISSING, asdict, fields, is_dataclass
from datetime import date, datetime
from enum import Enum
from types import NoneType, UnionType
from typing import TYPE_CHECKING, Any, get_args, get_origin, get_type_hints

if TYPE_CHECKING:  # a typing-only protocol: "any dataclass instance"
    from _typeshed import DataclassInstance


class DecodeError(ValueError):
    """Data that doesn't fit the schema, with a path like ``$.tasks[3].due``."""


def dumps(obj: object) -> str:
    return json.dumps(obj, default=_encode, indent=2, ensure_ascii=False) + "\n"


def _encode(value: object) -> object:
    # json calls this for any value it can't serialise itself, then serialises what we return,
    # calling us again for whatever *that* contains. A StrEnum never gets here: it is a str.
    match value:
        case date():  # datetime is a subclass of date, so this covers both
            return value.isoformat()
        case _ if is_dataclass(value) and not isinstance(value, type):
            return asdict(value)
    raise TypeError(f"can't encode {type(value).__name__} as JSON")


def loads[T: DataclassInstance](cls: type[T], text: str) -> T:
    return decode(cls, json.loads(text))


def decode[T: DataclassInstance](cls: type[T], data: object, path: str = "$") -> T:
    if not isinstance(data, dict):
        raise DecodeError(f"{path}: expected an object, got {_kind(data)}")
    hints = get_type_hints(cls)  # resolves the annotations into real types
    known = {f.name for f in fields(cls)}
    if unknown := data.keys() - known:
        raise DecodeError(f"{path}: unknown field(s) {', '.join(sorted(unknown))}")

    values: dict[str, Any] = {}
    for f in fields(cls):
        if f.name in data:
            values[f.name] = _convert(hints[f.name], data[f.name], f"{path}.{f.name}")
        elif f.default is MISSING and f.default_factory is MISSING:
            raise DecodeError(f"{path}.{f.name}: missing")
    return cls(**values)


def _convert(tp: Any, value: object, path: str) -> object:
    origin, args = get_origin(tp), get_args(tp)
    if origin is UnionType:  # `date | None`
        if value is None and NoneType in args:
            return None
        (inner,) = (arg for arg in args if arg is not NoneType)
        return _convert(inner, value, path)
    if origin is list:
        if not isinstance(value, list):
            raise DecodeError(f"{path}: expected a list, got {_kind(value)}")
        return [_convert(args[0], item, f"{path}[{i}]") for i, item in enumerate(value)]
    if isinstance(tp, type) and is_dataclass(tp):
        return decode(tp, value, path)
    if isinstance(tp, type) and issubclass(tp, Enum):
        try:
            return tp(value)
        except ValueError:
            choices = ", ".join(str(member.value) for member in tp)
            raise DecodeError(f"{path}: expected one of {choices}, got {value!r}") from None
    if tp in (date, datetime) and isinstance(value, str):
        try:
            return tp.fromisoformat(value)
        except ValueError:
            pass  # fall through to the error below
    # bool is a subclass of int, so isinstance(True, int) is True. Compare exact types instead.
    if tp in (str, int, bool) and type(value) is tp:
        return value
    raise DecodeError(f"{path}: expected {getattr(tp, '__name__', tp)}, got {value!r}")


def _kind(value: object) -> str:
    return type(value).__name__
