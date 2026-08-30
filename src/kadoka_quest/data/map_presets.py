from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from kadoka_quest.data.jsonio import read_json, write_json
from kadoka_quest.paths import DATA_ROOT


class MapPresetStore:
    def __init__(self, data_root: Path | None = None) -> None:
        self.root = Path(data_root or DATA_ROOT) / "map_presets"

    def list_ids(self) -> list[str]:
        return sorted(path.stem for path in self.root.glob("*.json"))

    def get(self, preset_id: str) -> dict[str, Any]:
        return read_json(self.root / f"{preset_id}.json")

    def save_from_map(
        self,
        preset_id: str,
        display_name: str,
        map_data: dict[str, Any],
        *,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        preset_id = self._validate_id(preset_id)
        display_name = self._validate_name(display_name)
        path = self.root / f"{preset_id}.json"
        if path.exists() and not overwrite:
            raise ValueError(f"Map preset already exists: {preset_id}")
        payload = deepcopy(map_data)
        payload["id"] = preset_id
        payload["display_name"] = display_name
        self._validate_document(payload)
        write_json(path, payload)
        return payload

    def apply_to_map(self, preset_id: str, target_map: dict[str, Any]) -> dict[str, Any]:
        target_id = str(target_map["id"])
        target_name = str(target_map["display_name"])
        payload = deepcopy(self.get(preset_id))
        self._validate_document(payload)
        payload["id"] = target_id
        payload["display_name"] = target_name
        return payload

    def build_map(self, preset_id: str, map_id: str, display_name: str) -> dict[str, Any]:
        map_id = self._validate_id(map_id)
        display_name = self._validate_name(display_name)
        payload = deepcopy(self.get(preset_id))
        self._validate_document(payload)
        payload["id"] = map_id
        payload["display_name"] = display_name
        return payload

    @staticmethod
    def _validate_id(value: str) -> str:
        value = str(value).strip()
        allowed = "abcdefghijklmnopqrstuvwxyz0123456789_-"
        if not value or any(character not in allowed for character in value):
            raise ValueError("Map preset id may contain only lowercase letters, digits, _ and -")
        return value

    @staticmethod
    def _validate_name(value: str) -> str:
        value = str(value).strip()
        if not value:
            raise ValueError("Map preset display name is required")
        return value

    @staticmethod
    def _validate_document(payload: dict[str, Any]) -> None:
        width = int(payload["width"])
        height = int(payload["height"])
        tiles = payload["tiles"]
        if not (5 <= width <= 200 and 5 <= height <= 200):
            raise ValueError("Map width and height must be between 5 and 200")
        if len(tiles) != height or any(len(row) != width for row in tiles):
            raise ValueError("Map tile dimensions do not match width and height")
        payload.setdefault("schema_version", 1)
        payload.setdefault("tile_size", 32)
        payload.setdefault("spawns", [])
        payload.setdefault("fixed_mobs", [])
        payload.setdefault("events", [])
