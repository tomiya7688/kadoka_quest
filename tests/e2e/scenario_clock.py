"""One explicit, monotonic timeline for test ticks and preset timestamps."""

from __future__ import annotations

from datetime import datetime, timedelta


def nonnegative_integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


class ScenarioClock:
    def __init__(self, start_ms: int) -> None:
        self.now = nonnegative_integer(start_ms, "start_ms")

    def ticks(self) -> int:
        return self.now

    def advance(self, milliseconds: int) -> None:
        self.now += nonnegative_integer(milliseconds, "ms")

    def datetime_now(self) -> datetime:
        return datetime(2000, 1, 1) + timedelta(milliseconds=self.now)
