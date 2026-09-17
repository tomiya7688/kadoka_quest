from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


PLAIN_SCALARS = (str, int, float, bool, type(None))


def is_plain_data(value: Any) -> bool:
    if isinstance(value, PLAIN_SCALARS):
        return True
    if isinstance(value, list):
        return all(is_plain_data(item) for item in value)
    if isinstance(value, Mapping):
        return all(isinstance(key, str) and is_plain_data(item) for key, item in value.items())
    return False


@dataclass(frozen=True)
class AppCommand:
    """Plain command exchanged between runtime applications."""

    target: str
    action: str
    payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not is_plain_data(self.payload):
            raise TypeError("command payload must contain only plain JSON-like data")
