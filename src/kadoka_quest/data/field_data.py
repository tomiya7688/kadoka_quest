from __future__ import annotations

from kadoka_quest.data.repository import GameRepository


class FieldDataLoader:
    """Load field maps and blocks and normalize a requested entry position."""

    def __init__(self, repository: GameRepository) -> None:
        self.repository = repository

    def blocks(self) -> dict[str, dict]:
        return {item["id"]: item for item in self.repository.list_blocks()}

    def load_map(self, map_id: str, x: int | None = None, y: int | None = None) -> dict:
        map_data = self.repository.get_map(str(map_id))
        requested_x = map_data["start"]["x"] if x is None else int(x)
        requested_y = map_data["start"]["y"] if y is None else int(y)
        return {
            "map": map_data,
            "x": max(0, min(int(map_data["width"]) - 1, requested_x)),
            "y": max(0, min(int(map_data["height"]) - 1, requested_y)),
        }
