from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class AppCommand:
    """Plain command exchanged between runtime applications."""

    target: str
    action: str
    payload: Mapping[str, Any] = field(default_factory=dict)
