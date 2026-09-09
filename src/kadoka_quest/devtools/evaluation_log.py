from __future__ import annotations

from typing import Any


class EvaluationLog:
    """Collect plain, serializable facts from an automated evaluation run."""

    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []

    def add(self, kind: str, step: int, **details: Any) -> None:
        self.entries.append({"step": int(step), "kind": str(kind), **details})

    def report(self, *, status: str, visited_maps: set[str], attempted_events: set[str]) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "kind": "game_evaluation",
            "status": status,
            "visited_maps": sorted(visited_maps),
            "attempted_events": sorted(attempted_events),
            "entries": self.entries,
        }
