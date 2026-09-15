from __future__ import annotations

from kadoka_quest.data.jsonio import read_json
from kadoka_quest.data.repository import GameRepository
from kadoka_quest.paths import DATA_ROOT


class FieldDataLoader:
    """Load field maps and blocks and normalize a requested entry position."""

    def __init__(self, repository: GameRepository) -> None:
        self.repository = repository

    def blocks(self) -> dict[str, dict]:
        return {item["id"]: item for item in self.repository.list_blocks()}

    @staticmethod
    def _additional_events(map_id: str) -> list[dict]:
        root = DATA_ROOT / "maps" / str(map_id) / "events"
        events: list[dict] = []
        if not root.is_dir():
            return events
        for path in sorted(root.glob("*.json")):
            try:
                payload = read_json(path)
            except (OSError, ValueError):
                continue
            values = payload.get("events") if isinstance(payload.get("events"), list) else [payload]
            events.extend(dict(event) for event in values if isinstance(event, dict) and event.get("id"))
        return events

    def load_map(self, map_id: str, x: int | None = None, y: int | None = None) -> dict:
        map_id = str(map_id)
        map_data = self.repository.get_map(map_id)
        additional_events = self._additional_events(map_id)
        if additional_events:
            map_data = dict(map_data)
            map_data["events"] = [*map_data.get("events", []), *additional_events]
        requested_x = map_data["start"]["x"] if x is None else int(x)
        requested_y = map_data["start"]["y"] if y is None else int(y)
        return {
            "map": map_data,
            "x": max(0, min(int(map_data["width"]) - 1, requested_x)),
            "y": max(0, min(int(map_data["height"]) - 1, requested_y)),
        }
