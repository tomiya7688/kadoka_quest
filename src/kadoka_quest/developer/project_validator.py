from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from kadoka_quest.data.jsonio import read_json
from kadoka_quest.data.repository import GameRepository, STAT_KEYS
from kadoka_quest.paths import ASSET_ROOT, DATA_ROOT


@dataclass(frozen=True)
class ValidationMessage:
    level: str
    location: str
    message: str

    def compact(self) -> str:
        return f"[{self.level}] {self.location}: {self.message}"


@dataclass(frozen=True)
class ValidationReport:
    messages: tuple[ValidationMessage, ...]

    @property
    def errors(self) -> tuple[ValidationMessage, ...]:
        return tuple(item for item in self.messages if item.level == "ERROR")

    @property
    def warnings(self) -> tuple[ValidationMessage, ...]:
        return tuple(item for item in self.messages if item.level == "WARN")

    @property
    def ok(self) -> bool:
        return not self.errors

    def summary(self, *, detail_limit: int = 3) -> str:
        state = "OK" if self.ok else "FAILED"
        head = f"Data validation {state}: {len(self.errors)} error(s), {len(self.warnings)} warning(s)"
        details = [item.compact() for item in self.messages[: max(0, detail_limit)]]
        return head if not details else head + " / " + " | ".join(details)


class ProjectValidator:
    """Validate the canonical Player data/assets without depending on pygame UI."""

    def __init__(self, data_root: Path | None = None, asset_root: Path | None = None) -> None:
        self.data_root = Path(data_root or DATA_ROOT)
        self.asset_root = Path(asset_root or ASSET_ROOT)
        self.repository = GameRepository(self.data_root)
        self._messages: list[ValidationMessage] = []

    def validate(self) -> ValidationReport:
        self._messages = []
        self._validate_json_files()
        self._validate_catalogs()
        return ValidationReport(tuple(self._messages))

    def _error(self, location: str, message: str) -> None:
        self._messages.append(ValidationMessage("ERROR", location, message))

    def _warn(self, location: str, message: str) -> None:
        self._messages.append(ValidationMessage("WARN", location, message))

    def _validate_json_files(self) -> None:
        if not self.data_root.is_dir():
            self._error("data", f"missing data directory: {self.data_root}")
            return
        json_files = sorted(self.data_root.rglob("*.json"))
        if not json_files:
            self._error("data", "no JSON files found")
            return
        for path in json_files:
            try:
                read_json(path)
            except (OSError, ValueError, TypeError) as exc:
                self._error(str(path.relative_to(self.data_root)), f"invalid JSON: {exc}")

    def _validate_catalogs(self) -> None:
        try:
            blocks = self.repository.list_blocks()
            maps = self.repository.list_maps()
            species_ids = self.repository.list_species_ids()
            skills = self.repository.get_skills()
            self.repository.get_equipment()
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self._error("catalog", f"repository load failed: {exc}")
            return

        block_ids = {str(item.get("id", "")) for item in blocks}
        if "" in block_ids:
            self._error("blocks", "block without id")
            block_ids.discard("")
        if len(block_ids) != len(blocks):
            self._error("blocks", "duplicate block id")

        species_set = set(species_ids)
        map_set = set(maps)
        for map_id in maps:
            self._validate_map(map_id, block_ids, species_set, map_set)
        for species_id in species_ids:
            self._validate_species(species_id, set(skills))

    def _validate_map(
        self,
        map_id: str,
        block_ids: set[str],
        species_ids: set[str],
        map_ids: set[str],
    ) -> None:
        location = f"maps/{map_id}"
        try:
            data = self.repository.get_map(map_id)
            width = int(data["width"])
            height = int(data["height"])
            tiles = data["tiles"]
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self._error(location, f"cannot load map: {exc}")
            return

        if str(data.get("id", "")) != map_id:
            self._error(location, f"map id does not match folder name: {data.get('id')!r}")
        if height <= 0 or width <= 0 or len(tiles) != height or any(len(row) != width for row in tiles):
            self._error(location, "tile dimensions do not match width/height")
            return

        unknown_blocks = {str(block_id) for row in tiles for block_id in row} - block_ids
        if unknown_blocks:
            self._error(location, "unknown block(s): " + ", ".join(sorted(unknown_blocks)))

        start = data.get("start", {})
        try:
            start_x, start_y = int(start["x"]), int(start["y"])
            if not (0 <= start_x < width and 0 <= start_y < height):
                self._error(location, "start position is outside the map")
        except (KeyError, TypeError, ValueError):
            self._error(location, "invalid start position")

        for index, entry in enumerate(self._iter_dicts(data.get("spawns", []))):
            species_id = str(entry.get("species_id", entry.get("species", "")))
            if species_id and species_id not in species_ids:
                self._error(f"{location}/spawns[{index}]", f"unknown species: {species_id}")
        for index, entry in enumerate(self._iter_dicts(data.get("fixed_mobs", []))):
            species_id = str(entry.get("species_id", entry.get("species", "")))
            if species_id and species_id not in species_ids:
                self._error(f"{location}/fixed_mobs[{index}]", f"unknown species: {species_id}")
        for index, entry in enumerate(self._iter_dicts(data.get("events", []))):
            target = str(entry.get("target_map", entry.get("map_id", "")))
            if target and target not in map_ids:
                self._error(f"{location}/events[{index}]", f"unknown target map: {target}")

    def _validate_species(self, species_id: str, skill_ids: set[str]) -> None:
        location = f"species/{species_id}"
        try:
            bundle = self.repository.get_species(species_id)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self._error(location, f"cannot load species bundle: {exc}")
            return

        if bundle.species_id != species_id:
            self._error(location, f"species id does not match folder name: {bundle.species_id!r}")

        levels = bundle.stats.get("levels", {})
        missing_levels = [str(level) for level in range(1, 101) if str(level) not in levels]
        if missing_levels:
            self._error(location, f"missing stat levels: {len(missing_levels)}")
        for level, values in levels.items():
            if not isinstance(values, dict):
                self._error(f"{location}/stats/{level}", "level stats must be an object")
                continue
            missing_stats = [key for key in STAT_KEYS if key not in values]
            if missing_stats:
                self._error(f"{location}/stats/{level}", "missing stat(s): " + ", ".join(missing_stats))
                break

        for index, entry in enumerate(self._iter_dicts(bundle.skills.get("learnset", []))):
            skill_id = str(entry.get("skill_id", ""))
            if skill_id and skill_id not in skill_ids:
                self._error(f"{location}/learnset[{index}]", f"unknown skill: {skill_id}")
        for stage_index, stage in enumerate(self._iter_dicts(bundle.plus.get("stages", []))):
            for option_index, option in enumerate(self._iter_dicts(stage.get("options", []))):
                if option.get("kind") == "skill":
                    skill_id = str(option.get("skill_id", ""))
                    if skill_id and skill_id not in skill_ids:
                        self._error(
                            f"{location}/plus[{stage_index}][{option_index}]",
                            f"unknown skill: {skill_id}",
                        )

        definition = bundle.definition
        asset_paths = [definition.get("portrait_path"), definition.get("field_sprite_path")]
        field_sprites = definition.get("field_sprites", {})
        if isinstance(field_sprites, dict):
            asset_paths.extend(field_sprites.values())
        for relative in dict.fromkeys(str(value) for value in asset_paths if value):
            if not (self.asset_root / relative).is_file():
                self._error(location, f"missing asset: {relative}")

    @staticmethod
    def _iter_dicts(value: object) -> Iterable[dict]:
        if not isinstance(value, list):
            return ()
        return (item for item in value if isinstance(item, dict))
