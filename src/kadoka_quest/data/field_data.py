from __future__ import annotations

from kadoka_quest.data.jsonio import read_json
from kadoka_quest.data.repository import GameRepository


class FieldDataLoader:
    """Load field maps and blocks and normalize a requested entry position."""

    def __init__(self, repository: GameRepository) -> None:
        self.repository = repository

    def blocks(self) -> dict[str, dict]:
        return {item["id"]: item for item in self.repository.list_blocks()}

    def species_ai_weights(self, map_data: dict) -> dict:
        species_ids = sorted({entry["species_id"] for entry in map_data.get("spawns", [])})
        return {
            species_id: self.repository.get_species(species_id).definition.get("field_ai_weights")
            for species_id in species_ids
        }

    def _additional_events(self, map_id: str) -> list[dict]:
        root = self.repository.root / "maps" / str(map_id) / "events"
        events: list[dict] = []
        if not root.is_dir():
            return events
        for path in sorted(root.glob("*.json")):
            try:
                payload = read_json(path)
            except (OSError, ValueError):
                continue
            if not isinstance(payload, dict):
                continue
            embedded = payload.get("events")
            values = embedded if isinstance(embedded, list) else [payload]
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
